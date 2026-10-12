"""Fixed local implementation dispatch; packet data never selects executable code."""

import hashlib

from zecsolve.domain.decision_rules import evaluate_decision
from zecsolve.domain.offline_evaluation import evaluate_offline
from zecsolve.domain.packets import ASSERTIONS, parse_packet
from zecsolve.replay.integrity import validate_history
from zecsolve.schemas.replay import ReplayCheckV1, ReplayResultV1
from zecsolve.schemas.resolution import MerchantCaseReportV1
from zecsolve.schemas.workflow_verification import OwnedAllocationV1

SUPPORTED_VERIFIER = ("zecsolve-verifier", "0.1.0", "1", "f6468e6d08a7adad53bf2991a311358dc84e869b")
SUPPORTED_RULES = {"0.1.0", "0.2.0"}
RUNTIME_FAILURES = {
    "VERIFIER_UNAVAILABLE",
    "VERIFIER_TIMEOUT",
    "VERIFIER_PROCESS_ERROR",
    "VERIFIER_OUTPUT_TOO_LARGE",
    "VERIFIER_PROTOCOL_ERROR",
}


def replay_packet(data: bytes, verifier):
    checks = []
    scoped = False

    def add(category, reference, status, code):
        checks.append(
            ReplayCheckV1(category=category, reference=str(reference), status=status, code=code)
        )

    def finish():
        states = {item.status for item in checks}
        status = (
            "FAILED"
            if "FAIL" in states
            else "UNSUPPORTED"
            if "UNSUPPORTED" in states
            else "LIMITED"
            if scoped or "MISSING" in states
            else "REPRODUCED"
        )
        return ReplayResultV1(
            status=status,
            full_replay=status == "REPRODUCED",
            packet_file_sha256=hashlib.sha256(data).hexdigest(),
            checks=checks,
            external_assertions=ASSERTIONS,
        )

    try:
        packet = parse_packet(data)
        validate_history(packet.payload)
    except (ValueError, KeyError, TypeError, RecursionError, OverflowError):
        add("integrity", "packet", "FAIL", "INVALID_PACKET_OR_HISTORY")
        return finish()
    add("integrity", "packet", "PASS", "PACKET_COMPONENT_AND_HISTORY_HASHES_MATCH")
    payload = packet.payload
    report = payload.report
    scoped = payload.replay_scope == "LIMITED"
    for _omission in payload.omissions:
        # Emit stable codes without reflecting arbitrary packet text into diagnostics.
        add("context", "disclosure", "MISSING", "DISCLOSED_SCOPE_OMITS_CONTEXT")
    declared = set()
    for item in payload.implementations.verifiers:
        identity = (item.name, item.version, item.result_schema_version, item.glasspane_revision)
        if any(value is None or value == "" for value in identity):
            add("context", "verifier", "MISSING", "VERIFIER_VERSION_METADATA_MISSING")
        elif identity != SUPPORTED_VERIFIER:
            add("context", "verifier", "UNSUPPORTED", "VERIFIER_IMPLEMENTATION_UNSUPPORTED")
        else:
            declared.add(identity)
    for version in payload.implementations.rules:
        if version not in SUPPORTED_RULES:
            add("context", "rules", "UNSUPPORTED", "RULES_IMPLEMENTATION_UNSUPPORTED")
    evidence = {item.evidence_id: item for item in payload.evidence}
    for item in report.verifications or []:
        result = item.result
        if (
            "schema_version" not in result.model_fields_set
            or "verifier" not in result.model_fields_set
            or not {"name", "version", "glasspane_revision"} <= result.verifier.model_fields_set
        ):
            add(
                "cryptographic_recovery",
                item.verification_id,
                "MISSING",
                "VERIFIER_VERSION_METADATA_MISSING",
            )
            continue
        identity = (
            result.verifier.name,
            result.verifier.version,
            result.schema_version,
            result.verifier.glasspane_revision,
        )
        reference = item.verification_id
        if identity != SUPPORTED_VERIFIER:
            add(
                "cryptographic_recovery",
                reference,
                "UNSUPPORTED",
                "VERIFIER_IMPLEMENTATION_UNSUPPORTED",
            )
            continue
        if identity not in declared:
            add("cryptographic_recovery", reference, "MISSING", "VERIFIER_DECLARATION_MISSING")
            continue
        inputs = evidence.get(item.evidence_id)
        if inputs is None or "OMITTED" in (
            inputs.receipt.availability,
            inputs.raw_transaction_hex.availability,
        ):
            add("cryptographic_recovery", reference, "MISSING", "ORIGINAL_INPUTS_WITHHELD")
            continue
        if result.reason_code in RUNTIME_FAILURES:
            add(
                "cryptographic_recovery",
                reference,
                "MISSING",
                "HISTORICAL_RUNTIME_FAILURE_NOT_REPRODUCIBLE",
            )
            continue
        actual = verifier.verify(inputs.receipt.text(), inputs.raw_transaction_hex.text())
        if actual.reason_code in RUNTIME_FAILURES:
            add("cryptographic_recovery", reference, "MISSING", "LOCAL_VERIFIER_UNAVAILABLE")
        elif actual != result:
            add("cryptographic_recovery", reference, "FAIL", "VERIFICATION_RESULT_MISMATCH")
        else:
            add(
                "cryptographic_recovery",
                reference,
                "PASS",
                "OUTPUT_RECOVERY_REPRODUCED"
                if actual.receipt_state == "VALID"
                else "NEGATIVE_RESULT_REPRODUCED",
            )
    if not isinstance(report, MerchantCaseReportV1):
        add("rules", "historical-context", "MISSING", "SCOPED_REPORT_WITHOUT_COMPLETE_RULE_INPUTS")
        return finish()

    def evaluate(reference, expected, flavor, *args):
        version = expected.rules_version
        if version not in payload.implementations.rules:
            add("rules", reference, "MISSING", "RULES_VERSION_DECLARATION_MISSING")
            return
        # Explicit historical dispatch: future rules cannot silently replace old arithmetic.
        handler = {
            ("offline", "0.1.0"): evaluate_offline,
            ("decision", "0.2.0"): evaluate_decision,
        }.get((flavor, version))
        if handler is None or args[0].policy.rules_version != "0.1.0":
            add("rules", reference, "UNSUPPORTED", "HISTORICAL_RULES_UNSUPPORTED")
            return
        try:
            matched = handler(*args) == expected
        except (ValueError, TypeError, OverflowError):
            matched = False
        add(
            "rules",
            reference,
            "PASS" if matched else "FAIL",
            "HISTORICAL_ARITHMETIC_REPRODUCED" if matched else "HISTORICAL_ARITHMETIC_MISMATCH",
        )

    for item in report.evaluations:
        context = item.inputs
        evaluate(
            item.evaluation_id,
            item.result,
            "offline",
            context.invoice,
            context.verification,
            context.approved_allocations,
            context.foreign_conflict,
        )
    for item in report.decisions:
        context = item.evaluation
        evaluate(
            context.evaluation_id,
            context.result,
            "decision",
            context.invoice,
            context.verification,
            context.approved_allocations,
            context.observation,
            context.evaluated_at,
            context.source_authorized,
            context.foreign_conflict,
        )
        allocations = list(context.approved_allocations)
        if item.action == "APPROVE_OUTPUT":
            output = context.verification.output if context.verification else None
            valid = (
                output is not None
                and context.result.eligible_for_credit
                and item.allocated_zat == output.amount_zat
                and item.output_id == output.identity
            )
            if valid:
                allocations.append(
                    OwnedAllocationV1(
                        output_id=output.identity,
                        invoice_id=context.invoice.invoice_id,
                        amount_zat=output.amount_zat,
                    )
                )
        else:
            valid = item.allocated_zat == 0 and item.output_id is None
        expected_state = {
            "APPROVE_OUTPUT": "RESOLVED" if item.balances.outstanding_zat == 0 else "UNDER_REVIEW",
            "REQUEST_EVIDENCE": "AWAITING_EVIDENCE",
            "REJECT_EVIDENCE": "UNDER_REVIEW",
            "CLOSE_UNRESOLVED": "CLOSED_UNRESOLVED",
        }[item.action]
        valid = valid and item.case_state == expected_state
        add(
            "rules",
            item.resolution_id,
            "PASS" if valid else "FAIL",
            "RECORDED_DECISION_TRANSITION_MATCHES" if valid else "DECISION_TRANSITION_MISMATCH",
        )
        evaluate(
            item.resolution_id,
            item.balances,
            "offline",
            context.invoice,
            context.verification,
            allocations,
            context.foreign_conflict,
        )
    if payload.balance_context is None:
        add("rules", "current-balance", "MISSING", "CURRENT_BALANCE_CONTEXT_MISSING")
    else:
        context = payload.balance_context
        selected = next(
            (
                item.result
                for item in report.verifications
                if item.verification_id == context.selected_verification_id
            ),
            None,
        )
        evaluate(
            "current-balance",
            report.balances,
            "offline",
            report.invoice,
            selected,
            context.approved_allocations,
            context.foreign_conflict,
        )
    add(
        "context",
        "observations-and-business-records",
        "EXTERNAL",
        "NO_FRESH_CHAIN_OR_AUTHOR_AUTHENTICATION",
    )
    return finish()
