import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_persisted_verification import verification_setup as verification_setup
from zecsolve.db.models import ChainObservation
from zecsolve.schemas.workflow_verification import CaseVerifyRequest

pytestmark = pytest.mark.postgres


def test_default_observer_records_unavailable_and_failure_never_reuses_success(
    database, verification_setup
):
    from zecsolve.services.observations import ObservationService

    service, principal, case, evidence, _ = verification_setup
    attempt, _ = service.verify(
        principal, case.case_id, CaseVerifyRequest(evidence_id=evidence.evidence_id), "verify"
    )
    recorder = ObservationService(database)
    offline = recorder.refresh(principal, case.case_id, attempt.verification_id)
    assert offline.state == "UNAVAILABLE" and offline.reason_code == "NO_CHAIN_OBSERVER"
    assert offline.txid == attempt.result.output.txid

    class FailingObserver:
        def observe(self, network, txid, raw_hash):
            raise OSError("private upstream detail")

    failed = ObservationService(database, FailingObserver()).refresh(
        principal, case.case_id, attempt.verification_id
    )
    assert failed.state == "UNAVAILABLE" and failed.reason_code == "OBSERVER_FAILED"
    assert "private upstream" not in failed.model_dump_json()
    with Session(database) as session:
        rows = list(session.scalars(select(ChainObservation)))
        assert len(rows) == 3
