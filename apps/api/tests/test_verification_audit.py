import uuid
from datetime import UTC, datetime

from zecsolve.domain.events import opening_event, submission_event, validate_event_chain


def test_verification_event_extends_evidence_history_with_safe_references():
    from zecsolve.domain.events import verification_event

    case, actor = uuid.uuid4(), uuid.uuid4()
    first = opening_event(
        event_id=uuid.uuid4(),
        case_id=case,
        credential_id=actor,
        invoice_id=uuid.uuid4(),
        invoice_snapshot_hash="ab" * 32,
        policy_id=uuid.uuid4(),
        at=datetime.now(UTC),
    )
    second = submission_event(
        event_id=uuid.uuid4(),
        case_id=case,
        credential_id=actor,
        evidence_id=uuid.uuid4(),
        payload_sha256="cd" * 32,
        sequence=2,
        case_version=2,
        case_state="OPEN",
        previous_hash=first.event_hash,
        at=datetime.now(UTC),
    )
    refs = {
        name: str(uuid.uuid4())
        for name in ("verification_id", "evidence_id", "observation_id", "evaluation_id")
    }
    third = verification_event(
        event_id=uuid.uuid4(),
        case_id=case,
        credential_id=actor,
        sequence=3,
        at=datetime.now(UTC),
        previous_hash=second.event_hash,
        payload={
            **refs,
            "result_sha256": "ef" * 32,
            "evaluation_sha256": "12" * 32,
            "case_version": 3,
            "case_state": "UNDER_REVIEW",
        },
    )
    validate_event_chain([first, second, third], case, 3)
    assert third.action == "VERIFICATION_RECORDED"
    assert "memo" not in str(third.payload) and "receipt" not in str(third.payload)
