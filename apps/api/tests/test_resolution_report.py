import pytest
from test_resolutions import (
    SimulatedObserver,
    approve,
    simulated_authority,
)
from test_resolutions import (
    resolution_setup as resolution_setup,
)
from test_resolutions import (
    verification_setup as verification_setup,
)
from zecsolve.services.reports import CaseReportService
from zecsolve.services.resolutions import ResolutionService

pytestmark = pytest.mark.postgres


def test_report_preserves_initial_and_decision_context_and_marks_simulation(
    database, resolution_setup
):
    principal, case, attempt = resolution_setup
    decision, _ = ResolutionService(database, SimulatedObserver(), simulated_authority).resolve(
        principal, case.case_id, approve(attempt), "approve"
    )
    report = CaseReportService(database).get(principal, case.case_id)
    assert report.report_scope == "SIMULATED_DECISIONS"
    assert report.decisions == [decision]
    assert report.decision_evaluations == [decision.evaluation]
    assert report.decision_observations == [decision.evaluation.observation]
    assert report.chain_observations[0].state == "UNAVAILABLE"
    assert report.evaluations[0].result.credited_zat == 0
    assert (
        report.balances.credited_zat,
        report.balances.outstanding_zat,
        report.balances.candidate_zat,
    ) == (100_000, 100_000, 0)
    assert report.events[-1].action == "RESOLUTION_RECORDED"
    assert '"ock"' not in report.model_dump_json()


def test_failed_offline_approval_observation_is_visible_without_a_decision(
    database, resolution_setup
):
    from zecsolve.services.workflow import WorkflowError

    principal, case, attempt = resolution_setup
    with pytest.raises(WorkflowError):
        ResolutionService(database).resolve(principal, case.case_id, approve(attempt), "blocked")
    report = CaseReportService(database).get(principal, case.case_id)
    assert report.report_scope == "INITIAL_OFFLINE" and report.decisions == []
    assert len(report.decision_observations) == 1
    assert report.decision_observations[0].reason_code == "NO_CHAIN_OBSERVER"
