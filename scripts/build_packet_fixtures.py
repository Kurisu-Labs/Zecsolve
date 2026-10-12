"""Deterministic PUBLIC/SYNTHETIC packet fixtures; never queries a database or chain."""

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from zecsolve.adapters.verifier import VerifierAdapter
from zecsolve.domain.decision_rules import evaluate_decision
from zecsolve.domain.events import (
    opening_event,
    scoped_submission_event,
    submission_event,
    verification_event,
)
from zecsolve.domain.offline_evaluation import evaluate_offline, evaluation_snapshot
from zecsolve.domain.packets import (
    ASSERTIONS,
    component,
    decoded_transaction_hash,
    implementations,
    seal_packet,
)
from zecsolve.domain.snapshots import canonical_bytes, digest
from zecsolve.schemas.case import CaseSummaryV1
from zecsolve.schemas.disclosure import ReviewerEvidenceV1, ReviewerReportV1, ReviewerVerificationV1
from zecsolve.schemas.evidence import (
    EvidenceStoredV1,
    EvidenceStoredV2,
    EvidenceSubmitRequest,
    EvidenceSubmitRequestV2,
)
from zecsolve.schemas.invoice import InvoicePolicyV1, InvoiceSnapshotV1, InvoiceTermsV1
from zecsolve.schemas.packet import (
    PacketBalanceContextV1,
    PacketEvidenceV1,
    PacketPayloadV1,
    PacketProvenanceV1,
)
from zecsolve.schemas.resolution import (
    DecisionObservationV1,
    DecisionObservationV2,
    DecisionSnapshotV1,
    MerchantCaseReportV1,
    ResolutionEventV1,
    ResolutionOutcomeV1,
)
from zecsolve.schemas.workflow_verification import (
    OfflineObservationV1,
    OwnedAllocationV1,
    ResolutionViewV1,
    VerificationAttemptV1,
)

ROOT = Path(__file__).resolve().parents[1]
AT = datetime(2026, 10, 12, tzinfo=UTC)


def identity(name):
    return uuid.uuid5(uuid.NAMESPACE_URL, "https://example.invalid/zecsolve-synthetic/" + name)


def hashed_snapshot(model):
    return model.model_copy(
        update={"snapshot_hash": digest(model.model_dump(mode="json", exclude={"snapshot_hash"}))}
    )


def build(current=False):
    receipt = (ROOT / "fixtures/mainnet/receipt.json").read_bytes().decode("utf-8")
    raw = (ROOT / "fixtures/mainnet/transaction.hex").read_bytes().decode("utf-8")
    result = VerifierAdapter(ROOT / "target/debug/zecsolve-verifier").verify(receipt, raw)
    assert result.receipt_state == "VALID", result.reason_code
    merchant, actor, case, evidence, verification = map(
        identity, ("merchant", "actor", "case", "evidence", "verification")
    )
    invoice = InvoiceSnapshotV1(
        invoice_id=identity("invoice"),
        merchant_id=merchant,
        policy_id=identity("policy"),
        created_at=AT,
        terms=InvoiceTermsV1(
            expected_zat=200_000,
            network="mainnet",
            pool="orchard",
            receiver_address=result.output.receiver_address,
            receiver_hex=result.output.receiver_hex,
            expected_memo="glasspane first receipt",
            memo_hex=result.output.memo_hex,
        ),
        policy=InvoicePolicyV1(),
        snapshot_hash="0" * 64,
    )
    invoice = invoice.model_copy(
        update={
            "snapshot_hash": digest(
                invoice.model_dump(mode="json", exclude={"created_at", "snapshot_hash"})
            )
        }
    )
    opening = opening_event(
        event_id=identity("open-event"),
        case_id=case,
        credential_id=actor,
        invoice_id=invoice.invoice_id,
        invoice_snapshot_hash=invoice.snapshot_hash,
        policy_id=invoice.policy_id,
        at=AT,
    )
    request_model = EvidenceSubmitRequestV2 if current else EvidenceSubmitRequest
    request = request_model(
        receipt_json=receipt,
        raw_tx_hex=raw,
        source="Public Glasspane fixture; synthetic case",
        source_kind="public_fixture",
        processing_authorized=True,
        disclosure_version="evidence-disclosure-v2" if current else "evidence-disclosure-v1",
        share_with_reviewers=current,
    )
    payload_hash = digest(request.model_dump(mode="json"))
    if current:
        submitted = scoped_submission_event(
            event_id=identity("submit-event"),
            case_id=case,
            actor="credential:" + str(actor),
            action="EVIDENCE_SUBMITTED",
            sequence=2,
            at=AT + timedelta(seconds=1),
            previous_hash=opening.event_hash,
            payload={
                "evidence_id": str(evidence),
                "payload_sha256": payload_hash,
                "consent_id": str(identity("consent")),
                "claim_id": None,
                "case_version": 2,
                "case_state": "OPEN",
            },
        )
    else:
        submitted = submission_event(
            event_id=identity("submit-event"),
            case_id=case,
            credential_id=actor,
            evidence_id=evidence,
            payload_sha256=payload_hash,
            sequence=2,
            case_version=2,
            case_state="OPEN",
            previous_hash=opening.event_hash,
            at=AT + timedelta(seconds=1),
        )
    metadata_model = EvidenceStoredV2 if current else EvidenceStoredV1
    extra = (
        {"actor_grant_id": None, "consent_id": identity("consent"), "claim_id": None}
        if current
        else {}
    )
    metadata = metadata_model(
        evidence_id=evidence,
        case_id=case,
        merchant_id=merchant,
        submitted_by=actor,
        submitted_at=submitted.at,
        source=request.source,
        source_kind=request.source_kind,
        disclosure_version=request.disclosure_version,
        processing_authorized=True,
        share_with_reviewers=current,
        receipt_sha256=hashlib.sha256(receipt.encode()).hexdigest(),
        raw_tx_hex_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        payload_sha256=payload_hash,
        case_version=2,
        case_state="OPEN",
        event_id=submitted.event_id,
        **extra,
    )
    observation = OfflineObservationV1(
        observation_id=identity("initial-observation"),
        verification_id=verification,
        observed_at=AT + timedelta(seconds=2),
        txid=result.output.txid,
        raw_tx_sha256=result.raw_tx_sha256,
    )
    evaluation = evaluation_snapshot(
        evaluation_id=identity("evaluation"),
        verification_id=verification,
        observation_id=observation.observation_id,
        case_id=case,
        merchant_id=merchant,
        at=observation.observed_at,
        invoice=invoice,
        report=result,
        allocations=[],
        foreign_conflict=False,
    )
    verified = verification_event(
        event_id=identity("verify-event"),
        case_id=case,
        credential_id=actor,
        sequence=3,
        at=observation.observed_at,
        previous_hash=submitted.event_hash,
        payload={
            "verification_id": str(verification),
            "evidence_id": str(evidence),
            "observation_id": str(observation.observation_id),
            "evaluation_id": str(evaluation.evaluation_id),
            "result_sha256": digest(result.model_dump(mode="json")),
            "evaluation_sha256": evaluation.snapshot_hash,
            "case_version": 3,
            "case_state": "UNDER_REVIEW",
        },
    )
    attempt = VerificationAttemptV1(
        verification_id=verification,
        evidence_id=evidence,
        case_id=case,
        merchant_id=merchant,
        actor_id=actor,
        created_at=verified.at,
        case_version=3,
        case_state="UNDER_REVIEW",
        result=result,
        observation=observation,
        evaluation=evaluation,
        event_id=verified.event_id,
    )
    simulated = DecisionObservationV1(
        observation_id=identity("simulated-observation"),
        verification_id=verification,
        observed_at=AT + timedelta(seconds=3),
        state="CONFIRMED",
        source_kind="SIMULATED",
        source="synthetic-packet-fixture",
        reason_code="SIMULATED_CONFIRMATION",
        txid=result.output.txid,
        raw_tx_sha256=result.raw_tx_sha256,
        confirmations=10,
        block_hash="ab" * 32,
        block_height=100,
    )
    decision_eval = hashed_snapshot(
        DecisionSnapshotV1(
            evaluation_id=identity("decision-evaluation"),
            case_id=case,
            merchant_id=merchant,
            evaluated_at=simulated.observed_at,
            invoice=invoice,
            verification_id=verification,
            verification=result,
            observation=simulated,
            source_authorized=True,
            approved_allocations=[],
            foreign_conflict=False,
            result=evaluate_decision(invoice, result, [], simulated, simulated.observed_at, True),
            snapshot_hash="0" * 64,
        )
    )
    owned = OwnedAllocationV1(
        output_id=result.output.identity, invoice_id=invoice.invoice_id, amount_zat=100_000
    )
    balances = evaluate_offline(invoice, result, [owned])
    decision = ResolutionOutcomeV1(
        resolution_id=identity("resolution"),
        case_id=case,
        merchant_id=merchant,
        invoice_id=invoice.invoice_id,
        actor_id=actor,
        action="APPROVE_OUTPUT",
        reason="Synthetic demonstration only",
        decided_at=simulated.observed_at,
        verification_id=verification,
        output_id=owned.output_id,
        allocated_zat=100_000,
        case_version=4,
        case_state="UNDER_REVIEW",
        evaluation=decision_eval,
        balances=balances,
        event_id=identity("decision-event"),
    )
    payload = {
        "resolution_id": str(decision.resolution_id),
        "evaluation_id": str(decision_eval.evaluation_id),
        "outcome_sha256": digest(decision.model_dump(mode="json")),
        "case_version": 4,
        "case_state": "UNDER_REVIEW",
    }
    decided = ResolutionEventV1(
        event_id=decision.event_id,
        case_id=case,
        sequence=4,
        actor="credential:" + str(actor),
        at=decision.decided_at,
        payload=payload,
        payload_hash=digest(payload),
        previous_hash=verified.event_hash,
        event_hash="0" * 64,
    )
    decided = decided.model_copy(
        update={
            "event_hash": digest(
                decided.model_dump(mode="json", exclude={"event_id", "payload", "event_hash"})
            )
        }
    )
    observations = [simulated]
    if current:
        observations.append(
            DecisionObservationV2(
                observation_id=identity("unavailable-rpc-shape"),
                verification_id=verification,
                observed_at=AT + timedelta(seconds=4),
                state="UNAVAILABLE",
                source="synthetic-unavailable-not-live",
                reason_code="RPC_SYNTHETIC_UNAVAILABLE",
                txid=result.output.txid,
                raw_tx_sha256=result.raw_tx_sha256,
                rpc={"fixture": "synthetic unavailable provenance shape; no node was queried"},
            )
        )
    from zecsolve.services.chain_review import chain_review

    report = MerchantCaseReportV1(
        report_scope="SIMULATED_DECISIONS",
        generated_at=AT + timedelta(seconds=5),
        case=CaseSummaryV1(
            case_id=case,
            invoice_id=invoice.invoice_id,
            merchant_id=merchant,
            state="UNDER_REVIEW",
            version=4,
            created_at=AT,
        ),
        invoice=invoice,
        policy=invoice.policy,
        claims=[],
        evidence=[metadata],
        verifications=[attempt],
        chain_observations=[observation],
        evaluations=[evaluation],
        selected_verification_id=verification,
        balances=balances,
        resolutions=[
            ResolutionViewV1(
                resolution_id=decision.resolution_id,
                outcome=decision.action,
                reason=decision.reason,
                approved_by="credential:" + str(actor),
                approved_at=decision.decided_at,
            )
        ],
        events=[opening, submitted, verified, decided],
        decision_observations=observations,
        decision_evaluations=[decision_eval],
        decisions=[decision],
        chain_review=chain_review([decision], observations),
    )
    inputs = PacketEvidenceV1(
        evidence_id=evidence,
        provenance=PacketProvenanceV1(
            source=metadata.source,
            source_kind=metadata.source_kind,
            submitted_at=metadata.submitted_at,
        ),
        receipt=component(receipt),
        raw_transaction_hex=component(raw),
        submission_payload=component(
            canonical_bytes(request.model_dump(mode="json")).decode("utf-8")
        ),
        decoded_transaction_sha256=decoded_transaction_hash(raw),
    )
    return seal_packet(
        PacketPayloadV1(
            disclosure_scope="MERCHANT",
            replay_scope="FULL_HISTORY",
            omissions=[],
            assertions=ASSERTIONS,
            report=report,
            evidence=[inputs],
            implementations=implementations(report),
            balance_context=PacketBalanceContextV1(
                selected_verification_id=verification,
                approved_allocations=[owned],
                foreign_conflict=False,
            ),
        )
    )


def scoped(packet):
    full = packet.payload.report
    item = full.evidence[0]
    report = ReviewerReportV1(
        case_id=full.case.case_id,
        generated_at=full.generated_at,
        sections=["evidence", "verifications"],
        evidence=[
            ReviewerEvidenceV1(
                evidence_id=item.evidence_id,
                submitted_at=item.submitted_at,
                source=item.source,
                source_kind=item.source_kind,
                receipt_sha256=item.receipt_sha256,
                raw_tx_hex_sha256=item.raw_tx_hex_sha256,
            )
        ],
        verifications=[
            ReviewerVerificationV1(
                verification_id=full.verifications[0].verification_id,
                evidence_id=item.evidence_id,
                result=full.verifications[0].result,
            )
        ],
    )
    evidence = packet.payload.evidence[0].model_copy(
        update={"submission_payload": component(None, omitted=True)}
    )
    return seal_packet(
        PacketPayloadV1(
            disclosure_scope="REVIEWER_SCOPED",
            replay_scope="LIMITED",
            omissions=[
                "UNSELECTED_SECTIONS_AND_EVIDENCE",
                "HISTORICAL_ALLOCATION_CONTEXT",
                "FULL_SUBMISSION_AND_AUDIT_HISTORY",
            ],
            assertions=ASSERTIONS,
            report=report,
            evidence=[evidence],
            balance_context=None,
            implementations=implementations(report),
        )
    )


if __name__ == "__main__":
    target = ROOT / "fixtures/packets"
    target.mkdir(exist_ok=True)
    legacy, current = build(), build(current=True)
    for name, packet in [
        ("complete-v1", legacy),
        ("complete-v2", current),
        ("scoped", scoped(current)),
    ]:
        (target / f"{name}.json").write_text(
            json.dumps(packet.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
        )
