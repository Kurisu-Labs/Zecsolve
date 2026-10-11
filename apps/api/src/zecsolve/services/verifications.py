import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from zecsolve.db.models import (
    Case,
    CaseEvent,
    CaseVerificationRequest,
    ChainObservation,
    Invoice,
    Verification,
    VerificationEvaluation,
)
from zecsolve.domain.events import verification_event
from zecsolve.domain.offline_evaluation import evaluate_offline, evaluation_snapshot
from zecsolve.domain.snapshots import digest
from zecsolve.schemas.verification import VerificationReport
from zecsolve.schemas.workflow_verification import OfflineObservationV1, VerificationAttemptV1
from zecsolve.services.audit import load_event_chain
from zecsolve.services.cases import load_owned_case
from zecsolve.services.evidence import EvidenceService, read_evidence_metadata
from zecsolve.services.invoices import read_invoice_snapshot
from zecsolve.services.verification_records import allocation_context, read_attempt
from zecsolve.services.workflow import (
    WorkflowError,
    authorize_merchant,
    transaction,
    validate_idempotency_key,
)


class VerificationService:
    def __init__(self, engine, cipher, verifier, slots):
        self.engine, self.verifier, self.slots = engine, verifier, slots
        self.evidence = EvidenceService(engine, cipher, slots)

    def replay(self, session, principal, case_id, key, request_hash):
        record = session.scalar(
            select(CaseVerificationRequest).where(
                CaseVerificationRequest.merchant_id == principal.merchant_id,
                CaseVerificationRequest.credential_id == principal.credential_id,
                CaseVerificationRequest.case_id == case_id,
                CaseVerificationRequest.idempotency_key == key,
            )
        )
        if record is None:
            return None
        if record.request_hash != request_hash:
            raise WorkflowError(409, "IDEMPOTENCY_CONFLICT")
        return read_attempt(session, principal, case_id, record.verification_id)

    def verify(self, principal, case_id, request, key):
        with transaction(self.engine) as session:
            authorize_merchant(session, principal)
            key = validate_idempotency_key(key)
            request_hash = digest(request.model_dump(mode="json"))
            previous = self.replay(session, principal, case_id, key, request_hash)
            if previous is not None:
                authorize_merchant(session, principal)
                return previous, True
            case = load_owned_case(session, principal, case_id)
            read_evidence_metadata(session, principal, case_id, request.evidence_id)
            if case.state in ("RESOLVED", "CLOSED_UNRESOLVED"):
                raise WorkflowError(409, "CASE_TERMINAL")
            invoice = read_invoice_snapshot(session, principal, case.invoice_id)
            try:
                evaluate_offline(invoice, None, [])
            except ValueError:
                raise WorkflowError(409, "RULES_VERSION_UNAVAILABLE") from None
            authorize_merchant(session, principal)
        # Decryption and subprocess execution hold no database transaction or row locks.
        content = self.evidence.read_content(principal, case_id, request.evidence_id)
        if not self.slots.acquire(blocking=False):
            raise WorkflowError(429, "VERIFIER_BUSY")
        try:
            report = self.verifier.verify(content.receipt_json, content.raw_tx_hex)
        finally:
            self.slots.release()
        report = VerificationReport.model_validate(report.model_dump(mode="json"))
        try:
            with transaction(self.engine) as session:
                authorize_merchant(session, principal)
                previous = self.replay(session, principal, case_id, key, request_hash)
                if previous is not None:
                    authorize_merchant(session, principal)
                    return previous, True
                case = load_owned_case(session, principal, case_id)
                parent = session.scalar(
                    select(Invoice)
                    .where(
                        Invoice.id == case.invoice_id, Invoice.merchant_id == principal.merchant_id
                    )
                    .with_for_update()
                )
                case = session.scalar(
                    select(Case)
                    .where(Case.id == case_id, Case.merchant_id == principal.merchant_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                authorize_merchant(session, principal)
                if (
                    case is None
                    or parent is None
                    or case.invoice_id != parent.id
                    or case.workflow_version != "1"
                ):
                    raise WorkflowError(409, "CASE_CONTEXT_UNAVAILABLE")
                previous = self.replay(session, principal, case_id, key, request_hash)
                if previous is not None:
                    authorize_merchant(session, principal)
                    return previous, True
                if case.state in ("RESOLVED", "CLOSED_UNRESOLVED"):
                    raise WorkflowError(409, "CASE_TERMINAL")
                read_evidence_metadata(session, principal, case_id, request.evidence_id)
                events = load_event_chain(session, case)
                invoice = read_invoice_snapshot(session, principal, parent.id)
                allocations, foreign = allocation_context(session, parent.id, report)
                now = session.scalar(select(func.clock_timestamp()))
                verification_id, observation_id, evaluation_id, event_id = [
                    uuid.uuid4() for _ in range(4)
                ]
                observation = OfflineObservationV1(
                    observation_id=observation_id,
                    verification_id=verification_id,
                    observed_at=now,
                    txid=report.output.txid if report.output else None,
                    raw_tx_sha256=report.raw_tx_sha256,
                )
                try:
                    evaluation = evaluation_snapshot(
                        evaluation_id=evaluation_id,
                        verification_id=verification_id,
                        observation_id=observation_id,
                        case_id=case_id,
                        merchant_id=principal.merchant_id,
                        at=now,
                        invoice=invoice,
                        report=report,
                        allocations=allocations,
                        foreign_conflict=foreign,
                    )
                except ValueError:
                    raise WorkflowError(409, "EVALUATION_UNAVAILABLE") from None
                case.version += 1
                if report.receipt_state in ("VALID", "INVALID"):
                    case.state = "UNDER_REVIEW"
                elif report.receipt_state == "NONE":
                    case.state = "AWAITING_EVIDENCE"
                event = verification_event(
                    event_id=event_id,
                    case_id=case_id,
                    credential_id=principal.credential_id,
                    sequence=case.version,
                    at=now,
                    previous_hash=events[-1].event_hash,
                    payload={
                        "verification_id": str(verification_id),
                        "evidence_id": str(request.evidence_id),
                        "observation_id": str(observation_id),
                        "evaluation_id": str(evaluation_id),
                        "result_sha256": digest(report.model_dump(mode="json")),
                        "evaluation_sha256": evaluation.snapshot_hash,
                        "case_version": case.version,
                        "case_state": case.state,
                    },
                )
                session.add(
                    Verification(
                        id=verification_id,
                        evidence_id=request.evidence_id,
                        case_id=case_id,
                        merchant_id=principal.merchant_id,
                        actor_id=principal.credential_id,
                        event_id=event_id,
                        workflow_version="1",
                        case_version=case.version,
                        case_state=case.state,
                        created_at=now,
                        receipt_state=report.receipt_state,
                        result=report.model_dump(mode="json"),
                        verifier_version=report.verifier.version,
                        rules_version=evaluation.result.rules_version,
                    )
                )
                session.flush()
                session.add(
                    ChainObservation(
                        id=observation_id,
                        verification_id=verification_id,
                        case_id=case_id,
                        merchant_id=principal.merchant_id,
                        state="UNAVAILABLE",
                        source="offline",
                        observed_at=now,
                        provenance=observation.model_dump(mode="json"),
                    )
                )
                session.flush()
                session.add(
                    VerificationEvaluation(
                        id=evaluation_id,
                        verification_id=verification_id,
                        observation_id=observation_id,
                        case_id=case_id,
                        merchant_id=principal.merchant_id,
                        invoice_id=parent.id,
                        policy_id=invoice.policy_id,
                        created_at=now,
                        snapshot=evaluation.model_dump(mode="json"),
                    )
                )
                session.add(
                    CaseEvent(
                        id=event_id,
                        case_id=case_id,
                        sequence=event.sequence,
                        actor=event.actor,
                        action=event.action,
                        at=now,
                        payload=event.payload,
                        payload_hash=event.payload_hash,
                        previous_hash=event.previous_hash,
                        event_hash=event.event_hash,
                        schema_version="1",
                    )
                )
                session.flush()
                session.add(
                    CaseVerificationRequest(
                        merchant_id=principal.merchant_id,
                        credential_id=principal.credential_id,
                        case_id=case_id,
                        idempotency_key=key,
                        request_hash=request_hash,
                        verification_id=verification_id,
                    )
                )
                session.flush()
                authorize_merchant(session, principal)
                result = VerificationAttemptV1(
                    verification_id=verification_id,
                    evidence_id=request.evidence_id,
                    case_id=case_id,
                    merchant_id=principal.merchant_id,
                    actor_id=principal.credential_id,
                    created_at=now,
                    case_version=case.version,
                    case_state=case.state,
                    result=report,
                    observation=observation,
                    evaluation=evaluation,
                    event_id=event_id,
                )
            return result, False
        except IntegrityError as error:
            if (
                getattr(getattr(error.orig, "diag", None), "constraint_name", None)
                != "uq_case_verification_key"
            ):
                raise
            with transaction(self.engine) as session:
                authorize_merchant(session, principal)
                previous = self.replay(session, principal, case_id, key, request_hash)
                if previous is None:
                    raise WorkflowError(409, "RETRY_VERIFICATION") from None
                authorize_merchant(session, principal)
                return previous, True
