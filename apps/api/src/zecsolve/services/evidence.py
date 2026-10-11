import hashlib
import uuid
from contextlib import contextmanager

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from zecsolve.adapters.evidence_crypto import EncryptedEvidence, EvidenceEncryptionError
from zecsolve.db.models import (
    Case,
    CaseEvent,
    Evidence,
    EvidenceContent,
    EvidenceSubmissionRequest,
    Invoice,
)
from zecsolve.domain.events import submission_event
from zecsolve.domain.snapshots import canonical_bytes
from zecsolve.schemas.evidence import (
    MAX_EVIDENCE_PAYLOAD_BYTES,
    EvidenceStoredV1,
    EvidenceSubmitRequest,
)
from zecsolve.services.audit import load_event_chain
from zecsolve.services.cases import CaseService
from zecsolve.services.workflow import (
    WorkflowError,
    authorize_merchant,
    transaction,
    validate_idempotency_key,
)


def content_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value is not None else None


class EvidenceService:
    def __init__(self, engine, cipher, slots):
        self.engine, self.cipher, self.slots = engine, cipher, slots
        self.cases = CaseService(engine)

    @contextmanager
    def crypto_slot(self):
        if not self.slots.acquire(blocking=False):
            raise WorkflowError(429, "EVIDENCE_BUSY")
        try:
            yield
        except EvidenceEncryptionError as error:
            code = str(error)
            status = (
                413
                if code == "EVIDENCE_TOO_LARGE"
                else (409 if code == "EVIDENCE_INTEGRITY_ERROR" else 503)
            )
            raise WorkflowError(status, code) from None
        finally:
            self.slots.release()

    def metadata(self, session, principal, case_id, evidence_id):
        self.cases.load(session, principal, case_id)
        row = session.scalar(
            select(Evidence).where(
                Evidence.id == evidence_id,
                Evidence.case_id == case_id,
                Evidence.merchant_id == principal.merchant_id,
            )
        )
        if row is None:
            raise WorkflowError(404, "EVIDENCE_NOT_FOUND")
        if row.bundle_version != "1" or row.bundle_metadata is None:
            raise WorkflowError(409, "LEGACY_EVIDENCE_UNAVAILABLE")
        try:
            metadata = EvidenceStoredV1.model_validate(row.bundle_metadata)
        except ValidationError:
            raise WorkflowError(409, "EVIDENCE_METADATA_UNAVAILABLE") from None
        if (
            metadata.evidence_id,
            metadata.case_id,
            metadata.merchant_id,
            metadata.submitted_by,
            metadata.payload_sha256,
        ) != (row.id, row.case_id, row.merchant_id, row.submitted_by, row.sha256):
            raise WorkflowError(409, "EVIDENCE_METADATA_UNAVAILABLE")
        return metadata

    def replay(self, session, principal, case_id, key, request_hash):
        record = session.scalar(
            select(EvidenceSubmissionRequest).where(
                EvidenceSubmissionRequest.merchant_id == principal.merchant_id,
                EvidenceSubmissionRequest.credential_id == principal.credential_id,
                EvidenceSubmissionRequest.case_id == case_id,
                EvidenceSubmissionRequest.idempotency_key == key,
            )
        )
        if record is None:
            return None
        if record.request_hash != request_hash:
            raise WorkflowError(409, "IDEMPOTENCY_CONFLICT")
        result = self.metadata(session, principal, case_id, record.evidence_id)
        if result.event_id != record.event_id:
            raise WorkflowError(409, "EVIDENCE_METADATA_UNAVAILABLE")
        return result

    def get(self, principal, case_id, evidence_id):
        with transaction(self.engine) as session:
            authorize_merchant(session, principal)
            result = self.metadata(session, principal, case_id, evidence_id)
            authorize_merchant(session, principal)
            return result

    def read_content(self, principal, case_id, evidence_id):
        with transaction(self.engine) as session:
            authorize_merchant(session, principal)
            metadata = self.metadata(session, principal, case_id, evidence_id)
            row = session.get(EvidenceContent, evidence_id)
            if row is None:
                raise WorkflowError(409, "EVIDENCE_CONTENT_UNAVAILABLE")
            sealed = EncryptedEvidence(row.key_id, row.nonce, row.ciphertext)
            authorize_merchant(session, principal)
        with self.crypto_slot():
            plaintext = self.cipher.decrypt(
                sealed, merchant_id=principal.merchant_id, case_id=case_id, evidence_id=evidence_id
            )
        try:
            request = EvidenceSubmitRequest.model_validate_json(plaintext)
        except ValueError:
            raise WorkflowError(409, "EVIDENCE_INTEGRITY_ERROR") from None
        if (
            hashlib.sha256(plaintext).hexdigest() != metadata.payload_sha256
            or content_hash(request.receipt_json) != metadata.receipt_sha256
            or content_hash(request.raw_tx_hex) != metadata.raw_tx_hex_sha256
        ):
            raise WorkflowError(409, "EVIDENCE_INTEGRITY_ERROR")
        with transaction(self.engine) as session:
            authorize_merchant(session, principal)
            self.metadata(session, principal, case_id, evidence_id)
            if (
                session.scalar(
                    select(EvidenceContent.evidence_id).where(
                        EvidenceContent.evidence_id == evidence_id
                    )
                )
                is None
            ):
                raise WorkflowError(409, "EVIDENCE_CONTENT_UNAVAILABLE")
            authorize_merchant(session, principal)
        return request

    def submit(self, principal, case_id, request: EvidenceSubmitRequest, key):
        with transaction(self.engine) as session:
            authorize_merchant(session, principal)
            key = validate_idempotency_key(key)
            payload = canonical_bytes(request.model_dump(mode="json"))
            if len(payload) > MAX_EVIDENCE_PAYLOAD_BYTES:
                raise WorkflowError(413, "EVIDENCE_TOO_LARGE")
            request_hash = hashlib.sha256(payload).hexdigest()
            previous = self.replay(session, principal, case_id, key, request_hash)
            if previous is not None:
                authorize_merchant(session, principal)
                return previous, True
            case = self.cases.load(session, principal, case_id)
            if case.state in ("RESOLVED", "CLOSED_UNRESOLVED"):
                raise WorkflowError(409, "CASE_TERMINAL")
            authorize_merchant(session, principal)
        identity = uuid.uuid4()
        with self.crypto_slot():
            sealed = self.cipher.encrypt(
                payload, merchant_id=principal.merchant_id, case_id=case_id, evidence_id=identity
            )
        try:
            with transaction(self.engine) as session:
                authorize_merchant(session, principal)
                previous = self.replay(session, principal, case_id, key, request_hash)
                if previous is not None:
                    authorize_merchant(session, principal)
                    return previous, True
                case = self.cases.load(session, principal, case_id)
                invoice = session.scalar(
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
                    or invoice is None
                    or case.invoice_id != invoice.id
                    or case.workflow_version != "1"
                ):
                    raise WorkflowError(409, "CASE_CONTEXT_UNAVAILABLE")
                previous = self.replay(session, principal, case_id, key, request_hash)
                if previous is not None:
                    authorize_merchant(session, principal)
                    return previous, True
                if case.state in ("RESOLVED", "CLOSED_UNRESOLVED"):
                    raise WorkflowError(409, "CASE_TERMINAL")
                events = load_event_chain(session, case)
                case.version += 1
                if case.state in ("OPEN", "AWAITING_EVIDENCE"):
                    case.state = (
                        "OPEN"
                        if request.receipt_json and request.raw_tx_hex
                        else "AWAITING_EVIDENCE"
                    )
                now = session.scalar(select(func.clock_timestamp()))
                event = submission_event(
                    event_id=uuid.uuid4(),
                    case_id=case_id,
                    credential_id=principal.credential_id,
                    evidence_id=identity,
                    payload_sha256=request_hash,
                    sequence=case.version,
                    case_version=case.version,
                    case_state=case.state,
                    previous_hash=events[-1].event_hash,
                    at=now,
                )
                metadata = EvidenceStoredV1(
                    evidence_id=identity,
                    case_id=case_id,
                    merchant_id=principal.merchant_id,
                    submitted_by=principal.credential_id,
                    submitted_at=now,
                    source=request.source,
                    source_kind=request.source_kind,
                    disclosure_version=request.disclosure_version,
                    processing_authorized=request.processing_authorized,
                    share_with_reviewers=False,
                    receipt_sha256=content_hash(request.receipt_json),
                    raw_tx_hex_sha256=content_hash(request.raw_tx_hex),
                    payload_sha256=request_hash,
                    case_version=case.version,
                    case_state=case.state,
                    event_id=event.event_id,
                )
                session.add(
                    Evidence(
                        id=identity,
                        case_id=case_id,
                        merchant_id=principal.merchant_id,
                        submitted_by=principal.credential_id,
                        type="encrypted_bundle",
                        source=request.source,
                        sha256=request_hash,
                        storage_ref=f"db:aesgcm:{identity}",
                        bundle_version="1",
                        bundle_metadata=metadata.model_dump(mode="json"),
                        created_at=now,
                    )
                )
                session.flush()
                session.add(
                    EvidenceContent(
                        evidence_id=identity,
                        key_id=sealed.key_id,
                        nonce=sealed.nonce,
                        ciphertext=sealed.ciphertext,
                    )
                )
                session.add(
                    CaseEvent(
                        id=event.event_id,
                        case_id=case_id,
                        sequence=event.sequence,
                        actor=event.actor,
                        action=event.action,
                        at=event.at,
                        payload=event.payload,
                        payload_hash=event.payload_hash,
                        previous_hash=event.previous_hash,
                        event_hash=event.event_hash,
                        schema_version="1",
                    )
                )
                session.flush()
                session.add(
                    EvidenceSubmissionRequest(
                        merchant_id=principal.merchant_id,
                        credential_id=principal.credential_id,
                        case_id=case_id,
                        idempotency_key=key,
                        request_hash=request_hash,
                        evidence_id=identity,
                        event_id=event.event_id,
                    )
                )
                session.flush()
                authorize_merchant(session, principal)
            return metadata, False
        except IntegrityError as error:
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if constraint == "uq_evidence_key_nonce":
                raise WorkflowError(409, "RETRY_EVIDENCE_SUBMISSION") from None
            if constraint != "uq_evidence_submission_key":
                raise
            with transaction(self.engine) as session:
                authorize_merchant(session, principal)
                previous = self.replay(session, principal, case_id, key, request_hash)
                if previous is None:
                    raise WorkflowError(409, "RETRY_EVIDENCE_SUBMISSION") from None
                authorize_merchant(session, principal)
                return previous, True
