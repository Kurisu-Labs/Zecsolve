import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError


def test_case_creation_accepts_only_invoice_reference():
    from zecsolve.schemas.case import CaseCreateRequest

    invoice = uuid.uuid4()
    assert CaseCreateRequest(invoice_id=str(invoice)).invoice_id == invoice
    for extra in (
        {"merchant_id": str(uuid.uuid4())},
        {"state": "RESOLVED"},
        {"actor": "attacker"},
        {"version": 2},
        {"payload": {}},
    ):
        with pytest.raises(ValidationError):
            CaseCreateRequest(invoice_id=invoice, **extra)


def test_opening_event_hashes_bind_payload_actor_time_and_case():
    from zecsolve.domain.events import opening_event
    from zecsolve.domain.snapshots import digest

    fields = dict(
        event_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        credential_id=uuid.uuid4(),
        invoice_id=uuid.uuid4(),
        invoice_snapshot_hash="ab" * 32,
        policy_id=uuid.uuid4(),
        at=datetime(2026, 10, 11, tzinfo=UTC),
    )
    event = opening_event(**fields)
    assert event.sequence == 1 and event.previous_hash is None
    assert event.action == "CASE_OPENED"
    assert event.actor == "credential:" + str(fields["credential_id"])
    assert event.payload == {
        "invoice_id": str(fields["invoice_id"]),
        "invoice_snapshot_hash": "ab" * 32,
        "policy_id": str(fields["policy_id"]),
    }
    assert event.payload_hash == digest(event.payload)
    expected = {
        "schema_version": "1",
        "case_id": str(fields["case_id"]),
        "sequence": 1,
        "actor": event.actor,
        "action": "CASE_OPENED",
        "at": "2026-10-11T00:00:00Z",
        "payload_hash": digest(event.payload),
        "previous_hash": None,
    }
    assert event.event_hash == digest(expected)
    for change in (
        {"case_id": uuid.uuid4()},
        {"credential_id": uuid.uuid4()},
        {"invoice_snapshot_hash": "cd" * 32},
        {"at": datetime(2026, 10, 12, tzinfo=UTC)},
    ):
        assert opening_event(**{**fields, **change}).event_hash != event.event_hash
    shifted = opening_event(**{**fields, "at": datetime.fromisoformat("2026-10-11T07:00:00+07:00")})
    assert shifted.event_hash == event.event_hash
