import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from zecsolve.adapters.chain import no_trusted_source
from zecsolve.db.models import (
    Case,
    CaseEvent,
    CaseResolutionRequest,
    DecisionEvaluation,
    Invoice,
    OutputAllocation,
    Resolution,
)
from zecsolve.domain.decision_rules import evaluate_decision
from zecsolve.domain.offline_evaluation import evaluate_offline
from zecsolve.domain.snapshots import digest
from zecsolve.schemas.resolution import DecisionSnapshotV1, ResolutionEventV1, ResolutionOutcomeV1
from zecsolve.schemas.workflow_verification import OwnedAllocationV1
from zecsolve.services.audit import load_event_chain
from zecsolve.services.cases import load_owned_case
from zecsolve.services.chain_review import read_chain_review
from zecsolve.services.invoices import read_invoice_snapshot
from zecsolve.services.observations import ObservationService, read_decision_observation
from zecsolve.services.resolution_records import read_resolution
from zecsolve.services.verification_records import allocation_context, read_attempt
from zecsolve.services.workflow import (
    WorkflowError,
    authorize_merchant,
    transaction,
    validate_idempotency_key,
)


class ResolutionService:
    def __init__(self, engine, observer=None, source_authority=None):
        self.engine = engine
        self.observations = ObservationService(engine, observer)
        self.source_authority = (
            source_authority if source_authority is not None else no_trusted_source
        )

    def replay(self, session, principal, case_id, key, request_hash):
        row = session.scalar(
            select(CaseResolutionRequest).where(
                CaseResolutionRequest.merchant_id == principal.merchant_id,
                CaseResolutionRequest.credential_id == principal.credential_id,
                CaseResolutionRequest.case_id == case_id,
                CaseResolutionRequest.idempotency_key == key,
            )
        )
        if row is None:
            return None
        if row.request_hash != request_hash:
            raise WorkflowError(409, "IDEMPOTENCY_CONFLICT")
        return read_resolution(session, principal, case_id, row.resolution_id)

    def bind_key(self, session, principal, case_id, key, request_hash, result):
        session.add(
            CaseResolutionRequest(
                merchant_id=principal.merchant_id,
                credential_id=principal.credential_id,
                case_id=case_id,
                idempotency_key=key,
                request_hash=request_hash,
                resolution_id=result.resolution_id,
            )
        )
        session.flush()

    def semantic_replay(self, session, principal, case, request, attempt):
        if request.action != "APPROVE_OUTPUT" or attempt.result.output is None:
            return None
        output = attempt.result.output
        allocation = session.get(
            OutputAllocation, (output.network, output.pool, output.txid, output.output_index)
        )
        if allocation is None:
            return None
        if allocation.invoice_id != case.invoice_id:
            raise WorkflowError(409, "OUTPUT_ALLOCATION_CONFLICT")
        return read_resolution(session, principal, case.id, allocation.resolution_id)

    def check_new(self, case, request):
        if case.state in ("RESOLVED", "CLOSED_UNRESOLVED"):
            raise WorkflowError(409, "CASE_TERMINAL")
        if case.version != request.expected_case_version:
            raise WorkflowError(
                409,
                "STALE_CASE_VERSION",
                {
                    "code": "STALE_CASE_VERSION",
                    "current_case_version": case.version,
                    "refresh": "Read the case report before submitting a new decision",
                },
            )

    def resolve(self, principal, case_id, request, key):
        try:
            return self._resolve(principal, case_id, request, key)
        except IntegrityError as error:
            name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if name not in ("output_allocations_pkey", "uq_case_resolution_key"):
                raise
            # The loser has rolled back all decision writes. Reauthorize the winning outcome.
            with transaction(self.engine) as session:
                authorize_merchant(session, principal)
                key = validate_idempotency_key(key)
                request_hash = digest(request.model_dump(mode="json"))
                result = self.replay(session, principal, case_id, key, request_hash)
                if result is None:
                    case = load_owned_case(session, principal, case_id)
                    attempt = (
                        read_attempt(session, principal, case_id, request.verification_id)
                        if request.verification_id
                        else None
                    )
                    result = self.semantic_replay(session, principal, case, request, attempt)
                    if result is None:
                        raise WorkflowError(409, "RETRY_RESOLUTION_OPERATION") from None
                    self.bind_key(session, principal, case_id, key, request_hash, result)
                authorize_merchant(session, principal)
                return result, True

    def _resolve(self, principal, case_id, request, key):
        request_hash = digest(request.model_dump(mode="json"))
        with transaction(self.engine) as session:
            authorize_merchant(session, principal)
            key = validate_idempotency_key(key)
            previous = self.replay(session, principal, case_id, key, request_hash)
            if previous is not None:
                authorize_merchant(session, principal)
                return previous, True
            case = load_owned_case(session, principal, case_id)
            attempt = (
                read_attempt(session, principal, case_id, request.verification_id)
                if request.verification_id
                else None
            )
            previous = self.semantic_replay(session, principal, case, request, attempt)
            if previous is not None:
                self.bind_key(session, principal, case_id, key, request_hash, previous)
                authorize_merchant(session, principal)
                return previous, True
            self.check_new(case, request)
            load_event_chain(session, case)
            authorize_merchant(session, principal)
        observation = None
        if request.action == "APPROVE_OUTPUT":
            observation = self.observations.refresh(principal, case_id, request.verification_id)
        with transaction(self.engine) as session:
            authorize_merchant(session, principal)
            previous = self.replay(session, principal, case_id, key, request_hash)
            if previous is not None:
                authorize_merchant(session, principal)
                return previous, True
            case = load_owned_case(session, principal, case_id)
            session.execute(
                select(Invoice).where(Invoice.id == case.invoice_id).with_for_update()
            ).scalar_one()
            case = session.scalar(
                select(Case)
                .where(Case.id == case_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            authorize_merchant(session, principal)
            previous = self.replay(session, principal, case_id, key, request_hash)
            attempt = (
                read_attempt(session, principal, case_id, request.verification_id)
                if request.verification_id
                else None
            )
            if previous is not None:
                authorize_merchant(session, principal)
                return previous, True
            previous = self.semantic_replay(session, principal, case, request, attempt)
            if previous is not None:
                self.bind_key(session, principal, case_id, key, request_hash, previous)
                authorize_merchant(session, principal)
                return previous, True
            self.check_new(case, request)
            events = load_event_chain(session, case)
            invoice = read_invoice_snapshot(session, principal, case.invoice_id)
            report = attempt.result if attempt else None
            allocations, foreign = allocation_context(session, case.invoice_id, report)
            now = session.scalar(select(func.clock_timestamp()))
            if observation:
                observation = read_decision_observation(
                    session, principal, case_id, observation.observation_id
                )
            if request.action == "APPROVE_OUTPUT" and read_chain_review(
                session, principal, case_id
            ):
                raise WorkflowError(409, "APPROVED_OUTPUT_CHAIN_REVIEW")
            authorized = self.source_authority(observation) is True if observation else False
            try:
                evaluated = evaluate_decision(
                    invoice, report, allocations, observation, now, authorized, foreign
                )
            except ValueError:
                raise WorkflowError(409, "EVALUATION_UNAVAILABLE") from None
            if request.action == "APPROVE_OUTPUT" and not evaluated.eligible_for_credit:
                raise WorkflowError(
                    409,
                    "CREDIT_INELIGIBLE",
                    {
                        "code": "CREDIT_INELIGIBLE",
                        "findings": evaluated.findings,
                        "observation_id": str(observation.observation_id),
                    },
                )
            return self.persist(
                session,
                principal,
                case,
                request,
                key,
                request_hash,
                invoice,
                report,
                observation,
                allocations,
                foreign,
                authorized,
                evaluated,
                events,
                now,
            ), False

    def persist(
        self,
        session,
        principal,
        case,
        request,
        key,
        request_hash,
        invoice,
        report,
        observation,
        allocations,
        foreign,
        authorized,
        evaluated,
        events,
        now,
    ):
        resolution_id, evaluation_id, event_id = (uuid.uuid4() for _ in range(3))
        snapshot = DecisionSnapshotV1(
            evaluation_id=evaluation_id,
            case_id=case.id,
            merchant_id=principal.merchant_id,
            evaluated_at=now,
            invoice=invoice,
            verification_id=request.verification_id,
            verification=report,
            observation=observation,
            source_authorized=authorized,
            approved_allocations=allocations,
            foreign_conflict=foreign,
            result=evaluated,
            snapshot_hash="0" * 64,
        )
        snapshot = snapshot.model_copy(
            update={
                "snapshot_hash": digest(snapshot.model_dump(mode="json", exclude={"snapshot_hash"}))
            }
        )
        output = report.output if request.action == "APPROVE_OUTPUT" else None
        post_allocations = allocations + (
            [
                OwnedAllocationV1(
                    output_id=output.identity,
                    invoice_id=case.invoice_id,
                    amount_zat=output.amount_zat,
                )
            ]
            if output
            else []
        )
        balances = evaluate_offline(invoice, report, post_allocations, foreign)
        case.version += 1
        case.state = {
            "APPROVE_OUTPUT": "RESOLVED" if balances.outstanding_zat == 0 else "UNDER_REVIEW",
            "REQUEST_EVIDENCE": "AWAITING_EVIDENCE",
            "REJECT_EVIDENCE": "UNDER_REVIEW",
            "CLOSE_UNRESOLVED": "CLOSED_UNRESOLVED",
        }[request.action]
        result = ResolutionOutcomeV1(
            resolution_id=resolution_id,
            case_id=case.id,
            merchant_id=principal.merchant_id,
            invoice_id=case.invoice_id,
            actor_id=principal.credential_id,
            action=request.action,
            reason=request.reason,
            decided_at=now,
            verification_id=request.verification_id,
            output_id=output.identity if output else None,
            allocated_zat=output.amount_zat if output else 0,
            case_version=case.version,
            case_state=case.state,
            evaluation=snapshot,
            balances=balances,
            event_id=event_id,
        )
        payload = {
            "resolution_id": str(resolution_id),
            "evaluation_id": str(evaluation_id),
            "outcome_sha256": digest(result.model_dump(mode="json")),
            "case_version": case.version,
            "case_state": case.state,
        }
        event = ResolutionEventV1(
            event_id=event_id,
            case_id=case.id,
            sequence=case.version,
            actor="credential:" + str(principal.credential_id),
            at=now,
            payload=payload,
            payload_hash=digest(payload),
            previous_hash=events[-1].event_hash,
            event_hash="0" * 64,
        )
        event = event.model_copy(
            update={
                "event_hash": digest(
                    event.model_dump(mode="json", exclude={"event_id", "payload", "event_hash"})
                )
            }
        )
        session.add(
            DecisionEvaluation(
                id=evaluation_id,
                case_id=case.id,
                merchant_id=principal.merchant_id,
                invoice_id=case.invoice_id,
                policy_id=invoice.policy_id,
                verification_id=request.verification_id,
                observation_id=observation.observation_id if observation else None,
                created_at=now,
                snapshot=snapshot.model_dump(mode="json"),
            )
        )
        session.flush()
        session.add(
            Resolution(
                id=resolution_id,
                case_id=case.id,
                merchant_id=principal.merchant_id,
                invoice_id=case.invoice_id,
                actor_id=principal.credential_id,
                verification_id=request.verification_id,
                evaluation_id=evaluation_id,
                event_id=event_id,
                workflow_version="1",
                outcome=request.action,
                reason=request.reason,
                approved_by=event.actor,
                approved_at=now,
                outcome_snapshot=result.model_dump(mode="json"),
            )
        )
        session.flush()
        if output:
            session.add(
                OutputAllocation(
                    network=output.network,
                    pool=output.pool,
                    txid=output.txid,
                    output_index=output.output_index,
                    invoice_id=case.invoice_id,
                    verification_id=request.verification_id,
                    resolution_id=resolution_id,
                    amount_zat=output.amount_zat,
                    case_id=case.id,
                    merchant_id=principal.merchant_id,
                )
            )
            session.flush()
        session.add(
            CaseEvent(
                id=event_id,
                case_id=case.id,
                sequence=case.version,
                actor=event.actor,
                action=event.action,
                at=now,
                payload_hash=event.payload_hash,
                previous_hash=event.previous_hash,
                event_hash=event.event_hash,
                schema_version=event.schema_version,
                payload=event.payload,
            )
        )
        session.flush()
        self.bind_key(session, principal, case.id, key, request_hash, result)
        authorize_merchant(session, principal)
        return result
