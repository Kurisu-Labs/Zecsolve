import hashlib
import uuid
from contextlib import contextmanager

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from zecsolve.adapters.evidence_crypto import EncryptedEvidence, EvidenceEncryptionError
from zecsolve.auth.access import authorize_case_access
from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.db.models import (
    AccessSubmissionRequest,
    CaseEvent,
    Evidence,
    EvidenceConsent,
    EvidenceContent,
    EvidenceSubmissionRequest,
)
from zecsolve.domain.events import scoped_submission_event, submission_event
from zecsolve.domain.snapshots import canonical_bytes
from zecsolve.schemas.evidence import (
    MAX_EVIDENCE_PAYLOAD_BYTES,
    EvidenceStoredV1,
    EvidenceStoredV2,
    EvidenceSubmitRequest,
    EvidenceSubmitRequestV2,
)
from zecsolve.services.audit import load_event_chain
from zecsolve.services.cases import CaseService, load_owned_case
from zecsolve.services.disclosure import project_evidence
from zecsolve.services.submissions import (
    actor_columns,
    actor_name,
    find_submission,
    lock_submission_case,
    validate_claim_link,
)
from zecsolve.services.workflow import (
    WorkflowError,
    transaction,
    validate_idempotency_key,
)


def content_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value is not None else None


def read_evidence_metadata(session, principal, case_id, evidence_id):
    load_owned_case(session, principal, case_id)
    row = session.scalar(
        select(Evidence).where(
            Evidence.id == evidence_id,
            Evidence.case_id == case_id,
            Evidence.merchant_id == principal.merchant_id,
        )
    )
    if row is None:
        raise WorkflowError(404, "EVIDENCE_NOT_FOUND")
    if row.bundle_version not in ("1", "2") or row.bundle_metadata is None:
        raise WorkflowError(409, "LEGACY_EVIDENCE_UNAVAILABLE")
    try:
        model = EvidenceStoredV1 if row.bundle_version == "1" else EvidenceStoredV2
        metadata = model.model_validate(row.bundle_metadata)
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
    if isinstance(metadata, EvidenceStoredV2):
        consent = session.get(EvidenceConsent, metadata.consent_id)
        if consent is None or (
            consent.evidence_id,
            consent.case_id,
            consent.merchant_id,
            consent.credential_id,
            consent.grant_id,
            consent.disclosure_version,
            consent.processing_authorized,
            consent.share_with_reviewers,
            consent.created_at,
            row.actor_grant_id,
        ) != (
            row.id,
            row.case_id,
            row.merchant_id,
            metadata.submitted_by,
            metadata.actor_grant_id,
            metadata.disclosure_version,
            metadata.processing_authorized,
            metadata.share_with_reviewers,
            metadata.submitted_at,
            metadata.actor_grant_id,
        ):
            raise WorkflowError(409, "EVIDENCE_CONSENT_UNAVAILABLE")
    elif row.actor_grant_id is not None:
        raise WorkflowError(409, "EVIDENCE_METADATA_UNAVAILABLE")
    return metadata


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
        return read_evidence_metadata(session, principal, case_id, evidence_id)

    def replay(self, session, principal, case_id, key, request_hash):
        record = find_submission(session, principal, case_id, "evidence", key, request_hash)
        if isinstance(principal, MerchantPrincipal):
            legacy = session.scalar(
                select(EvidenceSubmissionRequest).where(
                    EvidenceSubmissionRequest.merchant_id == principal.merchant_id,
                    EvidenceSubmissionRequest.credential_id == principal.credential_id,
                    EvidenceSubmissionRequest.case_id == case_id,
                    EvidenceSubmissionRequest.idempotency_key == key,
                )
            )
            if legacy is not None:
                if record is not None:
                    raise WorkflowError(409, "EVIDENCE_METADATA_UNAVAILABLE")
                record = legacy
        if record is None:
            return None
        if record.request_hash != request_hash:
            raise WorkflowError(409, "IDEMPOTENCY_CONFLICT")
        result = self.metadata(session, principal, case_id, record.evidence_id)
        if (
            result.event_id != record.event_id
            or result.submitted_by != getattr(principal, "credential_id", None)
            or getattr(result, "actor_grant_id", None) != getattr(principal, "grant_id", None)
        ):
            raise WorkflowError(409, "EVIDENCE_METADATA_UNAVAILABLE")
        return result

    def get(self, principal, case_id, evidence_id):
        with transaction(self.engine) as session:
            authorize_case_access(session, principal, case_id, "evidence:read", evidence_id)
            result = self.metadata(session, principal, case_id, evidence_id)
            authorize_case_access(session, principal, case_id, "evidence:read", evidence_id)
            return result if isinstance(principal, MerchantPrincipal) else project_evidence(result)

    def read_content(self, principal, case_id, evidence_id):
        with transaction(self.engine) as session:
            authorize_case_access(session, principal, case_id, "evidence:read", evidence_id)
            metadata = self.metadata(session, principal, case_id, evidence_id)
            row = session.get(EvidenceContent, evidence_id)
            if row is None:
                raise WorkflowError(409, "EVIDENCE_CONTENT_UNAVAILABLE")
            sealed = EncryptedEvidence(row.key_id, row.nonce, row.ciphertext)
            authorize_case_access(session, principal, case_id, "evidence:read", evidence_id)
        with self.crypto_slot():
            plaintext = self.cipher.decrypt(
                sealed, merchant_id=principal.merchant_id, case_id=case_id, evidence_id=evidence_id
            )
        try:
            model = (
                EvidenceSubmitRequestV2
                if isinstance(metadata, EvidenceStoredV2)
                else EvidenceSubmitRequest
            )
            request = model.model_validate_json(plaintext)
        except ValueError:
            raise WorkflowError(409, "EVIDENCE_INTEGRITY_ERROR") from None
        if (
            hashlib.sha256(plaintext).hexdigest() != metadata.payload_sha256
            or content_hash(request.receipt_json) != metadata.receipt_sha256
            or content_hash(request.raw_tx_hex) != metadata.raw_tx_hex_sha256
            or (
                request.source,
                request.source_kind,
                request.disclosure_version,
                request.processing_authorized,
                request.share_with_reviewers,
            )
            != (
                metadata.source,
                metadata.source_kind,
                metadata.disclosure_version,
                metadata.processing_authorized,
                metadata.share_with_reviewers,
            )
            or getattr(request, "claim_id", None) != getattr(metadata, "claim_id", None)
        ):
            raise WorkflowError(409, "EVIDENCE_INTEGRITY_ERROR")
        with transaction(self.engine) as session:
            authorize_case_access(session, principal, case_id, "evidence:read", evidence_id)
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
            authorize_case_access(session, principal, case_id, "evidence:read", evidence_id)
        return request

    def submit(
        self, principal, case_id, request: EvidenceSubmitRequest | EvidenceSubmitRequestV2, key
    ):
        scoped = isinstance(request, EvidenceSubmitRequestV2)
        with transaction(self.engine) as session:
            authorize_case_access(session, principal, case_id, "evidence:submit")
            if not isinstance(principal, MerchantPrincipal) and not scoped:
                raise WorkflowError(422, "CUSTOMER_DISCLOSURE_REQUIRED")
            key = validate_idempotency_key(key)
            payload = canonical_bytes(request.model_dump(mode="json"))
            if len(payload) > MAX_EVIDENCE_PAYLOAD_BYTES:
                raise WorkflowError(413, "EVIDENCE_TOO_LARGE")
            request_hash = hashlib.sha256(payload).hexdigest()
            previous = self.replay(session, principal, case_id, key, request_hash)
            if previous is not None:
                authorize_case_access(session, principal, case_id, "evidence:submit")
                return previous, True
            case = self.cases.load(session, principal, case_id)
            validate_claim_link(session, principal, case_id, getattr(request, "claim_id", None))
            if case.state in ("RESOLVED", "CLOSED_UNRESOLVED"):
                raise WorkflowError(409, "CASE_TERMINAL")
            authorize_case_access(session, principal, case_id, "evidence:submit")
        identity = uuid.uuid4()
        with self.crypto_slot():
            sealed = self.cipher.encrypt(
                payload, merchant_id=principal.merchant_id, case_id=case_id, evidence_id=identity
            )
        try:
            with transaction(self.engine) as session:
                authorize_case_access(session, principal, case_id, "evidence:submit")
                previous = self.replay(session, principal, case_id, key, request_hash)
                if previous is not None:
                    authorize_case_access(session, principal, case_id, "evidence:submit")
                    return previous, True
                case = lock_submission_case(session, principal, case_id, "evidence:submit")
                validate_claim_link(session, principal, case_id, getattr(request, "claim_id", None))
                previous = self.replay(session, principal, case_id, key, request_hash)
                if previous is not None:
                    authorize_case_access(session, principal, case_id, "evidence:submit")
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
                consent_id = uuid.uuid4() if scoped else None
                if scoped:
                    event = scoped_submission_event(
                        event_id=uuid.uuid4(),
                        case_id=case_id,
                        actor=actor_name(principal),
                        action="EVIDENCE_SUBMITTED",
                        sequence=case.version,
                        at=now,
                        previous_hash=events[-1].event_hash,
                        payload={
                            "evidence_id": str(identity),
                            "payload_sha256": request_hash,
                            "consent_id": str(consent_id),
                            "claim_id": str(request.claim_id) if request.claim_id else None,
                            "case_version": case.version,
                            "case_state": case.state,
                        },
                    )
                else:
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
                model = EvidenceStoredV2 if scoped else EvidenceStoredV1
                extra = (
                    {
                        "actor_grant_id": getattr(principal, "grant_id", None),
                        "consent_id": consent_id,
                        "claim_id": request.claim_id,
                    }
                    if scoped
                    else {}
                )
                metadata = model(
                    **extra,
                    evidence_id=identity,
                    case_id=case_id,
                    merchant_id=principal.merchant_id,
                    submitted_by=getattr(principal, "credential_id", None),
                    submitted_at=now,
                    source=request.source,
                    source_kind=request.source_kind,
                    disclosure_version=request.disclosure_version,
                    processing_authorized=request.processing_authorized,
                    share_with_reviewers=request.share_with_reviewers,
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
                        submitted_by=getattr(principal, "credential_id", None),
                        type="encrypted_bundle",
                        source=request.source,
                        sha256=request_hash,
                        storage_ref=f"db:aesgcm:{identity}",
                        actor_grant_id=getattr(principal, "grant_id", None),
                        bundle_version=metadata.schema_version,
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
                        schema_version=event.schema_version,
                    )
                )
                session.flush()
                if scoped:
                    session.add(
                        EvidenceConsent(
                            id=consent_id,
                            merchant_id=principal.merchant_id,
                            case_id=case_id,
                            evidence_id=identity,
                            **actor_columns(principal),
                            disclosure_version=request.disclosure_version,
                            processing_authorized=True,
                            share_with_reviewers=request.share_with_reviewers,
                            created_at=now,
                        )
                    )
                    session.add(
                        AccessSubmissionRequest(
                            merchant_id=principal.merchant_id,
                            case_id=case_id,
                            **actor_columns(principal),
                            operation="evidence",
                            evidence_id=identity,
                            event_id=event.event_id,
                            idempotency_key=key,
                            request_hash=request_hash,
                        )
                    )
                else:
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
                authorize_case_access(session, principal, case_id, "evidence:submit")
            return metadata, False
        except IntegrityError as error:
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if constraint == "uq_evidence_key_nonce":
                raise WorkflowError(409, "RETRY_EVIDENCE_SUBMISSION") from None
            if constraint not in (
                "uq_evidence_submission_key",
                "uq_access_credential_retry",
                "uq_access_grant_retry",
            ):
                raise
            with transaction(self.engine) as session:
                authorize_case_access(session, principal, case_id, "evidence:submit")
                previous = self.replay(session, principal, case_id, key, request_hash)
                if previous is None:
                    raise WorkflowError(409, "RETRY_EVIDENCE_SUBMISSION") from None
                authorize_case_access(session, principal, case_id, "evidence:submit")
                return previous, True
