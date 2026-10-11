from sqlalchemy import select

from zecsolve.db.models import DecisionEvaluation, OutputAllocation, Resolution
from zecsolve.domain.snapshots import digest
from zecsolve.schemas.resolution import ResolutionOutcomeV1
from zecsolve.services.audit import load_event_chain
from zecsolve.services.cases import load_owned_case
from zecsolve.services.invoices import read_invoice_snapshot
from zecsolve.services.observations import read_decision_observation
from zecsolve.services.verification_records import read_attempt
from zecsolve.services.workflow import WorkflowError


def read_resolution(session, principal, case_id, resolution_id):
    case = load_owned_case(session, principal, case_id)
    row = session.scalar(
        select(Resolution).where(
            Resolution.id == resolution_id,
            Resolution.case_id == case_id,
            Resolution.merchant_id == principal.merchant_id,
        )
    )
    if row is None:
        raise WorkflowError(404, "RESOLUTION_NOT_FOUND")
    try:
        if row.workflow_version != "1":
            raise ValueError("Legacy decision")
        result = ResolutionOutcomeV1.model_validate(row.outcome_snapshot)
        evaluation = session.get(DecisionEvaluation, row.evaluation_id)
        if evaluation is None or evaluation.snapshot != result.evaluation.model_dump(mode="json"):
            raise ValueError("Missing evaluation")
        if (
            result.resolution_id,
            result.case_id,
            result.merchant_id,
            result.invoice_id,
            result.actor_id,
            result.action,
            result.reason,
            result.decided_at,
            result.verification_id,
            result.evaluation.evaluation_id,
            result.event_id,
        ) != (
            row.id,
            case_id,
            principal.merchant_id,
            case.invoice_id,
            row.actor_id,
            row.outcome,
            row.reason,
            row.approved_at,
            row.verification_id,
            row.evaluation_id,
            row.event_id,
        ):
            raise ValueError("Decision metadata mismatch")
        if row.invoice_id != case.invoice_id or row.approved_by != "credential:" + str(
            result.actor_id
        ):
            raise ValueError("Decision ownership mismatch")
        snapshot = result.evaluation
        if (
            snapshot.case_id,
            snapshot.merchant_id,
            snapshot.verification_id,
            snapshot.evaluated_at,
        ) != (case_id, principal.merchant_id, result.verification_id, result.decided_at):
            raise ValueError("Evaluation linkage mismatch")
        if (
            evaluation.case_id,
            evaluation.merchant_id,
            evaluation.invoice_id,
            evaluation.policy_id,
            evaluation.verification_id,
            evaluation.observation_id,
            evaluation.created_at,
        ) != (
            case_id,
            principal.merchant_id,
            case.invoice_id,
            snapshot.invoice.policy_id,
            result.verification_id,
            snapshot.observation.observation_id if snapshot.observation else None,
            result.decided_at,
        ):
            raise ValueError("Evaluation metadata mismatch")
        if snapshot.snapshot_hash != digest(
            snapshot.model_dump(mode="json", exclude={"snapshot_hash"})
        ):
            raise ValueError("Evaluation hash mismatch")
        if snapshot.invoice != read_invoice_snapshot(session, principal, case.invoice_id):
            raise ValueError("Invoice mismatch")
        if result.verification_id:
            attempt = read_attempt(session, principal, case_id, result.verification_id)
            if snapshot.verification != attempt.result:
                raise ValueError("Verification mismatch")
        elif snapshot.verification is not None:
            raise ValueError("Unexpected verification")
        if snapshot.observation is not None:
            if snapshot.observation != read_decision_observation(
                session, principal, case_id, snapshot.observation.observation_id
            ):
                raise ValueError("Observation mismatch")
        events = load_event_chain(session, case)
        audit = next((event for event in events if event.event_id == row.event_id), None)
        if (
            audit is None
            or audit.action != "RESOLUTION_RECORDED"
            or audit.sequence != result.case_version
            or audit.actor != row.approved_by
            or audit.at != result.decided_at
            or audit.payload
            != {
                "resolution_id": str(row.id),
                "evaluation_id": str(row.evaluation_id),
                "outcome_sha256": digest(result.model_dump(mode="json")),
                "case_version": result.case_version,
                "case_state": result.case_state,
            }
        ):
            raise ValueError("Decision audit mismatch")
        allocations = list(
            session.scalars(
                select(OutputAllocation).where(OutputAllocation.resolution_id == row.id)
            )
        )
        if result.action == "APPROVE_OUTPUT":
            output = snapshot.verification.output
            if output is None or len(allocations) != 1 or not snapshot.result.eligible_for_credit:
                raise ValueError("Missing approved output")
            allocation = allocations[0]
            if (
                allocation.network,
                allocation.pool,
                allocation.txid,
                allocation.output_index,
                allocation.invoice_id,
                allocation.verification_id,
                allocation.amount_zat,
                allocation.case_id,
                allocation.merchant_id,
            ) != (
                output.network,
                output.pool,
                output.txid,
                output.output_index,
                case.invoice_id,
                result.verification_id,
                output.amount_zat,
                case_id,
                principal.merchant_id,
            ):
                raise ValueError("Allocation mismatch")
            if result.output_id != output.identity or result.allocated_zat != output.amount_zat:
                raise ValueError("Outcome allocation mismatch")
        elif allocations or result.output_id is not None or result.allocated_zat != 0:
            raise ValueError("Noncredit allocation")
        return result
    except (ValueError, AttributeError, TypeError):
        raise WorkflowError(409, "RESOLUTION_HISTORY_UNAVAILABLE") from None
