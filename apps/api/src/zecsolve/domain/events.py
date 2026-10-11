import uuid
from datetime import UTC, datetime

from zecsolve.domain.snapshots import digest
from zecsolve.schemas.case import CaseOpeningEventV1


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
