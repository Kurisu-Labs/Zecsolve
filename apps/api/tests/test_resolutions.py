from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_persisted_verification import verification_setup as verification_setup
from zecsolve.db.models import Case, CaseEvent, OutputAllocation, Resolution
from zecsolve.schemas.resolution import ResolveRequest
from zecsolve.schemas.workflow_verification import CaseVerifyRequest
from zecsolve.services.workflow import WorkflowError

pytestmark = pytest.mark.postgres


class SimulatedObserver:
    """Test-only confirmation; never imported by the deployed application."""

    def observe(self, network, txid, raw_hash):
        return dict(
            state="CONFIRMED",
            source_kind="SIMULATED",
            source="isolated-test",
            reason_code="SIMULATED_CONFIRMATION",
            observed_at=datetime.now(UTC),
            network=network,
            txid=txid,
            raw_tx_sha256=raw_hash,
            confirmations=10,
            block_hash="ab" * 32,
            block_height=100,
        )


def simulated_authority(observation):
    return observation.source_kind == "SIMULATED" and observation.source == "isolated-test"


@pytest.fixture
def resolution_setup(database, verification_setup):
    verifier, principal, case, evidence, _ = verification_setup
    attempt, _ = verifier.verify(
        principal, case.case_id, CaseVerifyRequest(evidence_id=evidence.evidence_id), "verify"
    )
    return principal, case, attempt


def approve(attempt, **changes):
    return ResolveRequest(
        **(
            dict(
                action="APPROVE_OUTPUT",
                verification_id=attempt.verification_id,
                expected_case_version=attempt.case_version,
                reason="Reviewed output",
            )
            | changes
        )
    )


def counts(database):
    with Session(database) as session:
        return [
            session.scalar(select(func.count()).select_from(model))
            for model in (Resolution, OutputAllocation, CaseEvent)
        ]


def test_offline_approval_is_blocked_without_partial_decision(database, resolution_setup):
    from zecsolve.services.resolutions import ResolutionService

    principal, case, attempt = resolution_setup
    with pytest.raises(WorkflowError) as error:
        ResolutionService(database).resolve(principal, case.case_id, approve(attempt), "approve")
    assert error.value.status == 409 and error.value.code == "CREDIT_INELIGIBLE"
    assert counts(database) == [0, 0, 3]


def test_simulated_partial_approval_and_semantic_replay_are_atomic(database, resolution_setup):
    from zecsolve.services.resolutions import ResolutionService

    principal, case, attempt = resolution_setup
    service = ResolutionService(database, SimulatedObserver(), simulated_authority)
    decision, replay = service.resolve(principal, case.case_id, approve(attempt), "approve")
    assert not replay and decision.allocated_zat == 100_000
    assert decision.case_state == "UNDER_REVIEW" and decision.case_version == 4
    assert (
        decision.balances.credited_zat,
        decision.balances.outstanding_zat,
        decision.balances.candidate_zat,
    ) == (100_000, 100_000, 0)
    assert decision.evaluation.result.credited_zat == 0
    service.observations.observer.observe = lambda *args: pytest.fail("Replay must not refresh")
    assert service.resolve(principal, case.case_id, approve(attempt), "approve") == (decision, True)
    assert service.resolve(principal, case.case_id, approve(attempt), "new-key") == (decision, True)
    with pytest.raises(WorkflowError) as error:
        service.resolve(principal, case.case_id, approve(attempt, reason="changed"), "new-key")
    assert error.value.code == "IDEMPOTENCY_CONFLICT"
    assert counts(database) == [1, 1, 4]


@pytest.mark.parametrize(
    "action,state",
    [
        ("REQUEST_EVIDENCE", "AWAITING_EVIDENCE"),
        ("REJECT_EVIDENCE", "UNDER_REVIEW"),
        ("CLOSE_UNRESOLVED", "CLOSED_UNRESOLVED"),
    ],
)
def test_noncredit_decisions_and_terminal_replay(database, resolution_setup, action, state):
    from zecsolve.services.resolutions import ResolutionService

    principal, case, attempt = resolution_setup
    request = ResolveRequest(
        action=action,
        expected_case_version=3,
        reason="Merchant decision",
        verification_id=attempt.verification_id if action == "REJECT_EVIDENCE" else None,
    )
    service = ResolutionService(database)
    result, replay = service.resolve(principal, case.case_id, request, "decision")
    assert not replay and result.case_state == state and result.allocated_zat == 0
    assert service.resolve(principal, case.case_id, request, "decision") == (result, True)
    assert counts(database) == [1, 0, 4]
    with Session(database) as session:
        assert session.get(Case, case.case_id).version == 4
