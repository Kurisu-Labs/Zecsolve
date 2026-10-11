from sqlalchemy import func, select, text

from zecsolve.db.models import ChainObservation, Claim, Evidence, Resolution, Verification
from zecsolve.domain.offline_evaluation import evaluate_offline
from zecsolve.schemas.case import CaseSummaryV1
from zecsolve.schemas.resolution import MerchantCaseReportV1
from zecsolve.schemas.workflow_verification import ClaimViewV1, ResolutionViewV1
from zecsolve.services.audit import load_event_chain
from zecsolve.services.cases import load_owned_case
from zecsolve.services.evidence import read_evidence_metadata
from zecsolve.services.invoices import read_invoice_snapshot
from zecsolve.services.observations import read_decision_observation
from zecsolve.services.resolution_records import read_resolution
from zecsolve.services.verification_records import allocation_context, read_attempt
from zecsolve.services.workflow import WorkflowError, authorize_merchant, transaction


class CaseReportService:
    def __init__(self, engine):
        self.engine = engine

    def get(self, principal, case_id, verification_id=None):
        with transaction(self.engine) as session:
            # A consistent snapshot; shared credential lock still enforces authorization.
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            authorize_merchant(session, principal)
            case = load_owned_case(session, principal, case_id)
            invoice = read_invoice_snapshot(session, principal, case.invoice_id)
            events = load_event_chain(session, case)
            evidence = []
            for row in session.scalars(
                select(Evidence)
                .where(Evidence.case_id == case_id)
                .order_by(Evidence.created_at, Evidence.id)
            ):
                if row.merchant_id != principal.merchant_id or row.bundle_version != "1":
                    raise WorkflowError(409, "LEGACY_EVIDENCE_UNAVAILABLE")
                evidence.append(read_evidence_metadata(session, principal, case_id, row.id))
            rows = list(
                session.scalars(
                    select(Verification)
                    .join(Evidence, Verification.evidence_id == Evidence.id)
                    .where(Evidence.case_id == case_id)
                    .order_by(Verification.case_version, Verification.id)
                )
            )
            attempts = []
            for row in rows:
                if (
                    row.workflow_version != "1"
                    or row.case_id != case_id
                    or row.merchant_id != principal.merchant_id
                ):
                    raise WorkflowError(409, "LEGACY_VERIFICATION_UNAVAILABLE")
                attempts.append(read_attempt(session, principal, case_id, row.id))
            selected = None
            if verification_id is not None:
                selected = next(
                    (item for item in attempts if item.verification_id == verification_id), None
                )
                if selected is None:
                    raise WorkflowError(404, "VERIFICATION_NOT_FOUND")
            elif attempts:
                selected = attempts[-1]
            result = selected.result if selected else None
            allocations, foreign = allocation_context(session, invoice.invoice_id, result)
            try:
                balances = evaluate_offline(invoice, result, allocations, foreign)
            except ValueError:
                raise WorkflowError(409, "EVALUATION_UNAVAILABLE") from None
            claims = [
                ClaimViewV1(
                    claim_id=row.id,
                    claimant_role=row.claimant_role,
                    reported_txid=row.reported_txid,
                    note=row.note,
                    created_at=row.created_at,
                )
                for row in session.scalars(
                    select(Claim)
                    .where(Claim.case_id == case_id)
                    .order_by(Claim.created_at, Claim.id)
                )
            ]
            resolutions = [
                ResolutionViewV1(
                    resolution_id=row.id,
                    outcome=row.outcome,
                    reason=row.reason,
                    approved_by=row.approved_by,
                    approved_at=row.approved_at,
                )
                for row in session.scalars(
                    select(Resolution)
                    .where(Resolution.case_id == case_id)
                    .order_by(Resolution.approved_at, Resolution.id)
                )
            ]
            decisions = [
                read_resolution(session, principal, case_id, row.id)
                for row in session.scalars(
                    select(Resolution)
                    .where(Resolution.case_id == case_id, Resolution.workflow_version == "1")
                    .order_by(Resolution.approved_at, Resolution.id)
                )
            ]
            initial_ids = {item.observation.observation_id for item in attempts}
            decision_observations = [
                read_decision_observation(session, principal, case_id, row.id)
                for row in session.scalars(
                    select(ChainObservation)
                    .where(
                        ChainObservation.case_id == case_id,
                        ChainObservation.merchant_id == principal.merchant_id,
                    )
                    .order_by(ChainObservation.observed_at, ChainObservation.id)
                )
                if row.id not in initial_ids
            ]
            scope = "INITIAL_OFFLINE"
            if decisions:
                scope = (
                    "SIMULATED_DECISIONS"
                    if any(
                        item.evaluation.observation
                        and item.evaluation.observation.source_kind == "SIMULATED"
                        for item in decisions
                    )
                    else "MERCHANT_DECISIONS"
                )
            report = MerchantCaseReportV1(
                report_scope=scope,
                decisions=decisions,
                decision_observations=decision_observations,
                decision_evaluations=[item.evaluation for item in decisions],
                generated_at=session.scalar(select(func.clock_timestamp())),
                case=CaseSummaryV1(
                    case_id=case.id,
                    invoice_id=case.invoice_id,
                    merchant_id=case.merchant_id,
                    state=case.state,
                    version=case.version,
                    created_at=case.created_at,
                ),
                invoice=invoice,
                policy=invoice.policy,
                claims=claims,
                evidence=evidence,
                verifications=attempts,
                chain_observations=[item.observation for item in attempts],
                evaluations=[item.evaluation for item in attempts],
                selected_verification_id=selected.verification_id if selected else None,
                balances=balances,
                resolutions=resolutions,
                events=events,
            )
            authorize_merchant(session, principal)
            return report
