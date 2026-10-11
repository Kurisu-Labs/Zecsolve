from pydantic import ValidationError
from sqlalchemy import select

from zecsolve.db.models import (
    CaseEvent,
    ChainObservation,
    OutputAllocation,
    Verification,
    VerificationEvaluation,
)
from zecsolve.domain.snapshots import digest
from zecsolve.schemas.verification import VerificationReport
from zecsolve.schemas.workflow_verification import (
    EvaluationSnapshotV1,
    OfflineObservationV1,
    OwnedAllocationV1,
    VerificationAttemptV1,
)
from zecsolve.services.cases import load_owned_case
from zecsolve.services.workflow import WorkflowError


def allocation_context(session, invoice_id, report):
    owned = [
        OwnedAllocationV1(
            output_id=f"{row.network}:{row.pool}:{row.txid}:{row.output_index}",
            invoice_id=row.invoice_id,
            amount_zat=row.amount_zat,
        )
        for row in session.scalars(
            select(OutputAllocation).where(OutputAllocation.invoice_id == invoice_id)
        )
    ]
    foreign = False
    if report is not None and report.output is not None:
        output = report.output
        allocated_to = session.scalar(
            select(OutputAllocation.invoice_id).where(
                OutputAllocation.network == output.network,
                OutputAllocation.pool == output.pool,
                OutputAllocation.txid == output.txid,
                OutputAllocation.output_index == output.output_index,
            )
        )
        foreign = allocated_to is not None and allocated_to != invoice_id
    return owned, foreign


def read_attempt(session, principal, case_id, verification_id):
    case = load_owned_case(session, principal, case_id)
    row = session.scalar(
        select(Verification).where(
            Verification.id == verification_id,
            Verification.case_id == case_id,
            Verification.merchant_id == principal.merchant_id,
        )
    )
    if row is None:
        raise WorkflowError(404, "VERIFICATION_NOT_FOUND")
    if row.workflow_version != "1":
        raise WorkflowError(409, "LEGACY_VERIFICATION_UNAVAILABLE")
    evaluation_row = session.scalar(
        select(VerificationEvaluation).where(
            VerificationEvaluation.verification_id == row.id,
            VerificationEvaluation.case_id == case_id,
            VerificationEvaluation.merchant_id == principal.merchant_id,
        )
    )
    if evaluation_row is None:
        raise WorkflowError(409, "VERIFICATION_HISTORY_UNAVAILABLE")
    observation_row = session.scalar(
        select(ChainObservation).where(
            ChainObservation.id == evaluation_row.observation_id,
            ChainObservation.verification_id == row.id,
            ChainObservation.case_id == case_id,
            ChainObservation.merchant_id == principal.merchant_id,
        )
    )
    event = session.scalar(
        select(CaseEvent).where(
            CaseEvent.id == row.event_id,
            CaseEvent.case_id == case_id,
            CaseEvent.action == "VERIFICATION_RECORDED",
        )
    )
    try:
        if observation_row is None or event is None:
            raise ValueError("Incomplete verification context")
        report = VerificationReport.model_validate(row.result)
        observation = OfflineObservationV1.model_validate(observation_row.provenance)
        evaluation = EvaluationSnapshotV1.model_validate(evaluation_row.snapshot)
        if (
            evaluation.evaluation_id,
            evaluation.verification_id,
            evaluation.observation_id,
            evaluation.case_id,
            evaluation.merchant_id,
        ) != (evaluation_row.id, row.id, observation_row.id, case_id, principal.merchant_id):
            raise ValueError("Evaluation linkage mismatch")
        if (
            evaluation.inputs.invoice.invoice_id,
            evaluation.inputs.invoice.policy_id,
            evaluation.inputs.invoice.merchant_id,
        ) != (case.invoice_id, evaluation_row.policy_id, principal.merchant_id):
            raise ValueError("Invoice linkage mismatch")
        if evaluation_row.invoice_id != case.invoice_id or evaluation.inputs.verification != report:
            raise ValueError("Evaluation input mismatch")
        if evaluation.snapshot_hash != digest(
            evaluation.model_dump(mode="json", exclude={"snapshot_hash"})
        ):
            raise ValueError("Evaluation hash mismatch")
        if (
            observation.observation_id,
            observation.verification_id,
            observation.state,
            observation.source,
        ) != (observation_row.id, row.id, observation_row.state, observation_row.source):
            raise ValueError("Observation linkage mismatch")
        if (
            observation.txid != (report.output.txid if report.output else None)
            or observation.raw_tx_sha256 != report.raw_tx_sha256
        ):
            raise ValueError("Observation binding mismatch")
        expected = {
            "verification_id": str(row.id),
            "evidence_id": str(row.evidence_id),
            "observation_id": str(observation_row.id),
            "evaluation_id": str(evaluation_row.id),
            "result_sha256": digest(report.model_dump(mode="json")),
            "evaluation_sha256": evaluation.snapshot_hash,
            "case_version": row.case_version,
            "case_state": row.case_state,
        }
        if (
            event.payload != expected
            or event.sequence != row.case_version
            or event.actor != "credential:" + str(row.actor_id)
        ):
            raise ValueError("Audit linkage mismatch")
        return VerificationAttemptV1(
            verification_id=row.id,
            evidence_id=row.evidence_id,
            case_id=case_id,
            merchant_id=principal.merchant_id,
            actor_id=row.actor_id,
            created_at=row.created_at,
            case_version=row.case_version,
            case_state=row.case_state,
            result=report,
            observation=observation,
            evaluation=evaluation,
            event_id=row.event_id,
        )
    except (ValueError, ValidationError):
        raise WorkflowError(409, "VERIFICATION_HISTORY_UNAVAILABLE") from None
