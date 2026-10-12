from sqlalchemy import func, select, text

from zecsolve.auth.access import authorize_case_access
from zecsolve.db.models import ChainObservation, Claim, Resolution, Verification
from zecsolve.domain.offline_evaluation import evaluate_offline
from zecsolve.schemas.disclosure import (
    ReviewerCaseV1,
    ReviewerClaimV1,
    ReviewerDecisionV1,
    ReviewerEvaluationV1,
    ReviewerEventV1,
    ReviewerInvoiceV1,
    ReviewerReportV1,
    ReviewerVerificationV1,
)
from zecsolve.services.audit import load_event_chain
from zecsolve.services.cases import load_owned_case
from zecsolve.services.claims import validate_claim_record
from zecsolve.services.disclosure import (
    project_evidence,
    project_observation,
    selected_evidence,
    shared_claim_event,
)
from zecsolve.services.evidence import read_evidence_metadata
from zecsolve.services.invoices import read_invoice_snapshot
from zecsolve.services.observations import read_decision_observation
from zecsolve.services.resolution_records import read_resolution
from zecsolve.services.verification_records import allocation_context, read_attempt
from zecsolve.services.workflow import WorkflowError, transaction


class ReviewerReportService:
    def __init__(self, engine):
        self.engine = engine

    def get(self, principal, case_id, verification_id=None):
        with transaction(self.engine) as session:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            context = authorize_case_access(session, principal, case_id, "report:read")
            result = self.assemble(session, principal, case_id, context, verification_id)
            authorize_case_access(session, principal, case_id, "report:read")
            selected_evidence(session, principal, case_id, context)
            return result

    def assemble(self, session, principal, case_id, context, verification_id=None):
        sections = set(context.report_sections)
        allowed = selected_evidence(session, principal, case_id, context)
        case = load_owned_case(session, principal, case_id)
        events = load_event_chain(session, case)
        visible_events = set()
        data = {}
        if "case" in sections:
            data["case"] = ReviewerCaseV1(
                state=case.state, version=case.version, created_at=case.created_at
            )
        invoice = None
        if sections & {"invoice", "balances"}:
            invoice = read_invoice_snapshot(session, principal, case.invoice_id)
        if "invoice" in sections:
            data["invoice"] = ReviewerInvoiceV1(terms=invoice.terms, policy=invoice.policy)
        if "claims" in sections:
            data["claims"] = []
            for claim in session.scalars(
                select(Claim).where(Claim.case_id == case_id).order_by(Claim.created_at, Claim.id)
            ):
                validate_claim_record(claim, events)
                event = shared_claim_event(claim, events)
                if event:
                    data["claims"].append(
                        ReviewerClaimV1(
                            claim_id=claim.id,
                            reported_txid=claim.reported_txid,
                            note=claim.note,
                            created_at=claim.created_at,
                        )
                    )
                    visible_events.add(event.event_id)
        if "evidence" in sections:
            metadata = [
                read_evidence_metadata(session, principal, case_id, item)
                for item in sorted(allowed)
            ]
            data["evidence"] = [project_evidence(item) for item in metadata]
            visible_events.update(item.event_id for item in metadata)
        attempts = []
        if (
            sections & {"verifications", "observations", "evaluations", "balances", "decisions"}
            or verification_id
        ):
            for row in session.scalars(
                select(Verification)
                .where(
                    Verification.case_id == case_id,
                    Verification.merchant_id == principal.merchant_id,
                    Verification.evidence_id.in_(allowed),
                )
                .order_by(Verification.case_version, Verification.id)
            ):
                attempts.append(read_attempt(session, principal, case_id, row.id))
        selected = (
            next((item for item in attempts if item.verification_id == verification_id), None)
            if verification_id
            else (attempts[-1] if attempts else None)
        )
        if verification_id and selected is None:
            raise WorkflowError(404, "VERIFICATION_NOT_FOUND")
        ids = {item.verification_id for item in attempts}
        if "verifications" in sections:
            data["verifications"] = [
                ReviewerVerificationV1(
                    verification_id=item.verification_id,
                    evidence_id=item.evidence_id,
                    result=item.result,
                )
                for item in attempts
            ]
            visible_events.update(item.event_id for item in attempts)
        if "observations" in sections:
            initial = {item.observation.observation_id for item in attempts}
            data["observations"] = [item.observation for item in attempts] + [
                read_decision_observation(session, principal, case_id, row.id)
                for row in session.scalars(
                    select(ChainObservation)
                    .where(
                        ChainObservation.case_id == case_id,
                        ChainObservation.verification_id.in_(ids),
                    )
                    .order_by(ChainObservation.observed_at, ChainObservation.id)
                )
                if row.id not in initial
            ]
            data["observations"] = [project_observation(item) for item in data["observations"]]
        if "evaluations" in sections:
            data["evaluations"] = [
                ReviewerEvaluationV1(
                    verification_id=item.verification_id,
                    evaluated_at=item.evaluation.evaluated_at,
                    result=item.evaluation.result,
                )
                for item in attempts
            ]
        if "balances" in sections:
            result = selected.result if selected else None
            allocations, foreign = allocation_context(session, case.invoice_id, result)
            try:
                data["balances"] = evaluate_offline(invoice, result, allocations, foreign)
            except ValueError:
                raise WorkflowError(409, "EVALUATION_UNAVAILABLE") from None
        if "decisions" in sections:
            data["decisions"] = []
            for row in session.scalars(
                select(Resolution)
                .where(Resolution.case_id == case_id, Resolution.workflow_version == "1")
                .order_by(Resolution.approved_at, Resolution.id)
            ):
                if row.verification_id is not None and row.verification_id not in ids:
                    continue
                item = read_resolution(session, principal, case_id, row.id)
                observation = item.evaluation.observation
                data["decisions"].append(
                    ReviewerDecisionV1(
                        resolution_id=item.resolution_id,
                        verification_id=item.verification_id,
                        action=item.action,
                        reason=item.reason,
                        decided_at=item.decided_at,
                        allocated_zat=item.allocated_zat,
                        source_kind=observation.source_kind if observation else None,
                    )
                )
                visible_events.add(item.event_id)
        if "events" in sections:
            data["events"] = [
                ReviewerEventV1(event_id=item.event_id, action=item.action, at=item.at)
                for item in events
                if item.event_id in visible_events
            ]
        return ReviewerReportV1(
            case_id=case_id,
            generated_at=session.scalar(select(func.clock_timestamp())),
            sections=context.report_sections,
            **data,
        )
