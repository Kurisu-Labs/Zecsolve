import uuid

import pytest
from pydantic import ValidationError


def test_verification_request_cannot_supply_trusted_fields():
    from zecsolve.schemas.workflow_verification import CaseVerifyRequest

    evidence = uuid.uuid4()
    assert CaseVerifyRequest(evidence_id=evidence).evidence_id == evidence
    for extra in (
        {"chain_state": "CONFIRMED"},
        {"amount_zat": 100000},
        {"merchant_id": str(uuid.uuid4())},
        {"confirmed": True},
    ):
        with pytest.raises(ValidationError):
            CaseVerifyRequest(evidence_id=evidence, **extra)


def test_offline_observation_cannot_claim_confirmation():
    from datetime import UTC, datetime

    from zecsolve.schemas.workflow_verification import OfflineObservationV1

    base = dict(
        observation_id=uuid.uuid4(), verification_id=uuid.uuid4(), observed_at=datetime.now(UTC)
    )
    assert OfflineObservationV1(**base).state == "UNAVAILABLE"
    for change in (
        {"state": "CONFIRMED"},
        {"confirmations": 10},
        {"source": "caller"},
        {"block_height": 1},
    ):
        with pytest.raises(ValidationError):
            OfflineObservationV1(**base, **change)
