import uuid
from datetime import UTC, datetime

import pytest
from zecsolve.domain.events import opening_event


def test_evidence_event_continues_hash_chain_and_binds_case_version():
    from zecsolve.domain.events import submission_event, validate_event_chain

    case = uuid.uuid4()
    credential = uuid.uuid4()
    first = opening_event(
        event_id=uuid.uuid4(),
        case_id=case,
        credential_id=credential,
        invoice_id=uuid.uuid4(),
        invoice_snapshot_hash="ab" * 32,
        policy_id=uuid.uuid4(),
        at=datetime.now(UTC),
    )
    second = submission_event(
        event_id=uuid.uuid4(),
        case_id=case,
        credential_id=credential,
        evidence_id=uuid.uuid4(),
        payload_sha256="cd" * 32,
        sequence=2,
        case_version=2,
        case_state="OPEN",
        previous_hash=first.event_hash,
        at=datetime.now(UTC),
    )
    validate_event_chain([first, second], case, 2)
    assert set(second.payload) == {"evidence_id", "payload_sha256", "case_version", "case_state"}
    for changed in [
        second.model_copy(update={"previous_hash": "00" * 32}),
        second.model_copy(update={"sequence": 3}),
        second.model_copy(update={"payload": {**second.payload, "payload_sha256": "ef" * 32}}),
    ]:
        with pytest.raises(ValueError):
            validate_event_chain([first, changed], case, 2)
    with pytest.raises(ValueError):
        validate_event_chain([first, second], uuid.uuid4(), 2)
    with pytest.raises(ValueError):
        validate_event_chain([first, second], case, 3)
