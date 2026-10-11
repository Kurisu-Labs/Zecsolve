import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import event, insert
from test_persisted_verification import verification_setup as verification_setup
from zecsolve.db.models import OutputAllocation
from zecsolve.schemas.evidence import EvidenceSubmitRequest
from zecsolve.schemas.workflow_verification import CaseVerifyRequest
from zecsolve.services.workflow import WorkflowError

pytestmark = pytest.mark.postgres


def test_initial_and_verified_case_reports_show_honest_offline_balances(
    database, verification_setup
):
    from zecsolve.services.reports import CaseReportService

    service, principal, case, evidence, _ = verification_setup
    reports = CaseReportService(database)
    empty = reports.get(principal, case.case_id)
    assert empty.selected_verification_id is None and empty.verifications == []
    assert empty.balances.candidate_zat == 0 and empty.balances.outstanding_zat == 200_000
    attempt, _ = service.verify(
        principal, case.case_id, CaseVerifyRequest(evidence_id=evidence.evidence_id), "verify"
    )
    result = reports.get(principal, case.case_id)
    assert result.selected_verification_id == attempt.verification_id
    assert result.case.version == 3 and result.case.state == "UNDER_REVIEW"
    assert (
        len(result.events) == 3
        and len(result.verifications)
        == len(result.evaluations)
        == len(result.chain_observations)
        == 1
    )
    assert (
        result.balances.credited_zat,
        result.balances.candidate_zat,
        result.balances.projected_outstanding_zat,
    ) == (0, 100_000, 100_000)
    assert result.balances.eligible_for_credit is False
    assert (
        "receipt_json" not in result.model_dump_json() and '"ock"' not in result.model_dump_json()
    )
    with pytest.raises(WorkflowError) as error:
        reports.get(principal, case.case_id, uuid.uuid4())
    assert error.value.status == 404


def test_report_redacts_foreign_allocation_and_keeps_historical_evaluation(
    database, verification_setup
):
    from test_postgres import allocation, seed
    from zecsolve.services.reports import CaseReportService

    service, principal, case, evidence, _ = verification_setup
    attempt, _ = service.verify(
        principal, case.case_id, CaseVerifyRequest(evidence_id=evidence.evidence_id), "verify"
    )
    foreign = seed(database)[0]
    # Synthetic allocation context exercises reads, not live chain confirmation.
    record = allocation(foreign)
    record.update(txid=attempt.result.output.txid, output_index=attempt.result.output.output_index)
    with database.begin() as connection:
        connection.execute(insert(OutputAllocation).values(**record))
    report = CaseReportService(database).get(principal, case.case_id)
    assert "DUPLICATE_CLAIM" in report.balances.findings and report.balances.candidate_zat == 0
    assert report.evaluations[0].result.candidate_zat == 100_000
    assert str(foreign["invoice_id"]) not in report.model_dump_json()


def test_report_snapshot_does_not_mix_concurrent_submission(
    database, verification_setup, receipt, raw_tx
):
    from zecsolve.services.reports import CaseReportService

    _, principal, case, _, evidence = verification_setup
    triggered = threading.Event()
    role = threading.local()
    request = EvidenceSubmitRequest(
        receipt_json=receipt, raw_tx_hex=raw_tx, source="concurrent", processing_authorized=True
    )

    def concurrent_upload():
        role.name = "writer"
        return evidence.submit(principal, case.case_id, request, "concurrent")

    def after_select(connection, cursor, statement, parameters, context, executemany):
        if (
            getattr(role, "name", None) != "writer"
            and "FROM cases" in statement
            and not triggered.is_set()
        ):
            triggered.set()
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(concurrent_upload).result(timeout=10)

    event.listen(database, "after_cursor_execute", after_select)
    try:
        report = CaseReportService(database).get(principal, case.case_id)
    finally:
        event.remove(database, "after_cursor_execute", after_select)
    assert triggered.is_set()
    assert report.case.version == 2 and len(report.evidence) == 1 and len(report.events) == 2
    latest = CaseReportService(database).get(principal, case.case_id)
    assert latest.case.version == 3 and len(latest.evidence) == 2 and len(latest.events) == 3
