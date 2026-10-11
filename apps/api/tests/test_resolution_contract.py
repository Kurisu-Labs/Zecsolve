import uuid

import pytest
from pydantic import ValidationError


def test_resolution_input_enforces_action_reference_and_server_authority():
    from zecsolve.schemas.resolution import ResolveRequest

    valid = dict(
        action="APPROVE_OUTPUT",
        verification_id=uuid.uuid4(),
        expected_case_version=3,
        reason="Reviewed payment",
    )
    assert ResolveRequest(**valid).reason == "Reviewed payment"
    for update in (
        {"verification_id": None},
        {"reason": " "},
        {"reason": "a\0b"},
        {"reason": "x" * 2001},
        {"expected_case_version": True},
        {"expected_case_version": 0},
        {"amount_zat": 100},
        {"chain_state": "CONFIRMED"},
        {"actor_id": str(uuid.uuid4())},
    ):
        with pytest.raises(ValidationError):
            ResolveRequest(**(valid | update))
    for action in ("REQUEST_EVIDENCE", "CLOSE_UNRESOLVED"):
        with pytest.raises(ValidationError):
            ResolveRequest(**(valid | {"action": action}))
        assert ResolveRequest(**(valid | {"action": action, "verification_id": None}))
    with pytest.raises(ValidationError):
        ResolveRequest(**(valid | {"action": "REJECT_EVIDENCE", "verification_id": None}))
