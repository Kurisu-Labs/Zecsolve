import uuid
from datetime import UTC, datetime

from zecsolve.domain.snapshots import digest
from zecsolve.schemas.case import CaseOpeningEventV1
from zecsolve.schemas.evidence import EvidenceSubmittedEventV1
from zecsolve.schemas.submission import SubmissionEventV2
from zecsolve.schemas.workflow_verification import VerificationEventV1


def opening_event(
    *,
    event_id: uuid.UUID,
    case_id: uuid.UUID,
    credential_id: uuid.UUID,
    invoice_id: uuid.UUID,
    invoice_snapshot_hash: str,
    policy_id: uuid.UUID,
    at: datetime,
) -> CaseOpeningEventV1:
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("Event time must include a timezone")
    payload = {
        "invoice_id": str(invoice_id),
        "invoice_snapshot_hash": invoice_snapshot_hash,
        "policy_id": str(policy_id),
    }
    # No receipt, memo, receiver, token, or foreign-case detail belongs in the event.
    event = CaseOpeningEventV1(
        event_id=event_id,
        case_id=case_id,
        actor="credential:" + str(credential_id),
        at=at.astimezone(UTC),
        payload=payload,
        payload_hash=digest(payload),
        event_hash="0" * 64,
    )
    header = event.model_dump(mode="json", exclude={"event_id", "payload", "event_hash"})
    return event.model_copy(update={"event_hash": digest(header)})


def submission_event(
    *,
    event_id,
    case_id,
    credential_id,
    evidence_id,
    payload_sha256,
    sequence,
    case_version,
    case_state,
    previous_hash,
    at,
):
    if at.tzinfo is None or at.utcoffset() is None or sequence != case_version:
        raise ValueError("Invalid event time or version")
    event = EvidenceSubmittedEventV1(
        event_id=event_id,
        case_id=case_id,
        sequence=sequence,
        actor="credential:" + str(credential_id),
        at=at,
        previous_hash=previous_hash,
        payload={
            "evidence_id": str(evidence_id),
            "payload_sha256": payload_sha256,
            "case_version": case_version,
            "case_state": case_state,
        },
        payload_hash="0" * 64,
        event_hash="0" * 64,
    )
    event = event.model_copy(update={"payload_hash": digest(event.payload)})
    header = event.model_dump(mode="json", exclude={"event_id", "payload", "event_hash"})
    return event.model_copy(update={"event_hash": digest(header)})


def validate_event_chain(events, case_id, case_version):
    if not events or len(events) != case_version:
        raise ValueError("Case version does not match event history")
    previous = None
    for sequence, event in enumerate(events, start=1):
        header = event.model_dump(mode="json", exclude={"event_id", "payload", "event_hash"})
        if (
            event.case_id != case_id
            or event.sequence != sequence
            or event.previous_hash != previous
            or event.payload_hash != digest(event.payload)
            or event.event_hash != digest(header)
        ):
            raise ValueError("Invalid case event chain")
        if sequence == 1 and event.action != "CASE_OPENED":
            raise ValueError("Missing opening event")
        if sequence > 1 and event.payload["case_version"] != sequence:
            raise ValueError("Event version mismatch")
        previous = event.event_hash


def scoped_submission_event(
    *, event_id, case_id, actor, action, sequence, at, previous_hash, payload
):
    event = SubmissionEventV2(
        event_id=event_id,
        case_id=case_id,
        actor=actor,
        action=action,
        sequence=sequence,
        at=at,
        previous_hash=previous_hash,
        payload=payload,
        payload_hash=digest(payload),
        event_hash="0" * 64,
    )
    header = event.model_dump(mode="json", exclude={"event_id", "payload", "event_hash"})
    return event.model_copy(update={"event_hash": digest(header)})


def verification_event(*, event_id, case_id, credential_id, sequence, at, previous_hash, payload):
    if at.tzinfo is None or at.utcoffset() is None or payload.get("case_version") != sequence:
        raise ValueError("Invalid event time or version")
    event = VerificationEventV1(
        event_id=event_id,
        case_id=case_id,
        sequence=sequence,
        actor="credential:" + str(credential_id),
        at=at,
        payload=payload,
        payload_hash=digest(payload),
        previous_hash=previous_hash,
        event_hash="0" * 64,
    )
    return event.model_copy(
        update={
            "event_hash": digest(
                event.model_dump(mode="json", exclude={"event_id", "payload", "event_hash"})
            )
        }
    )
