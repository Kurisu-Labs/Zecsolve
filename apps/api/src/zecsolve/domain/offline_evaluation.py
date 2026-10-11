from dataclasses import asdict

from zecsolve.domain.rules import RULES_VERSION, ApprovedAllocation, InvoiceTerms, evaluate
from zecsolve.domain.snapshots import digest
from zecsolve.schemas.verification import VerificationReport
from zecsolve.schemas.workflow_verification import (
    EvaluationInputsV1,
    EvaluationSnapshotV1,
    OfflineEvaluationV1,
)


def evaluate_offline(invoice, report, allocations, foreign_conflict=False):
    if invoice.policy.rules_version != RULES_VERSION:
        raise ValueError("Unsupported historical rules version")
    if any(item.invoice_id != invoice.invoice_id for item in allocations):
        raise ValueError("Only owned allocation records may enter scoped evaluation")
    approved = tuple(
        ApprovedAllocation(item.output_id, str(item.invoice_id), item.amount_zat)
        for item in allocations
    )
    if foreign_conflict:
        if report is None or report.output is None:
            raise ValueError("Foreign conflict requires a recovered output")
        # An opaque conflict marker, not a foreign invoice/amount disclosure.
        approved += (ApprovedAllocation(report.output.identity, "external-allocation", 0),)
    terms = invoice.terms
    evaluation = evaluate(
        InvoiceTerms(
            str(invoice.invoice_id),
            terms.expected_zat,
            terms.network,
            terms.pool,
            terms.receiver_hex,
            terms.memo_hex,
            False,
        ),
        report or VerificationReport(receipt_state="NONE", reason_code="NO_VERIFICATION_ATTEMPT"),
        approved,
    )
    return OfflineEvaluationV1(**asdict(evaluation))


def evaluation_snapshot(
    *,
    evaluation_id,
    verification_id,
    observation_id,
    case_id,
    merchant_id,
    at,
    invoice,
    report,
    allocations,
    foreign_conflict,
):
    snapshot = EvaluationSnapshotV1(
        evaluation_id=evaluation_id,
        verification_id=verification_id,
        observation_id=observation_id,
        case_id=case_id,
        merchant_id=merchant_id,
        evaluated_at=at,
        inputs=EvaluationInputsV1(
            invoice=invoice,
            verification=report,
            approved_allocations=allocations,
            foreign_conflict=foreign_conflict,
        ),
        result=evaluate_offline(invoice, report, allocations, foreign_conflict),
        snapshot_hash="0" * 64,
    )
    return snapshot.model_copy(
        update={
            "snapshot_hash": digest(snapshot.model_dump(mode="json", exclude={"snapshot_hash"}))
        }
    )
