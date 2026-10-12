import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session
from test_customer_submissions import ORIGIN, claim_request
from test_customer_submissions import submissions as submissions
from test_evidence_service import evidence_setup as evidence_setup
from test_persisted_verification import verification_setup as verification_setup
from test_resolutions import (
    SimulatedObserver,
    approve,
    simulated_authority,
)
from test_resolutions import (
    resolution_setup as resolution_setup,
)
from test_reviewer_reports import SECTIONS, reviewer
from zecsolve.adapters.verifier import VerifierAdapter
from zecsolve.auth.credentials import MerchantPrincipal, provision_merchant, revoke_credential
from zecsolve.config import Settings
from zecsolve.domain.packets import parse_packet
from zecsolve.main import create_app
from zecsolve.replay.engine import replay_packet
from zecsolve.schemas.workflow_verification import CaseVerifyRequest
from zecsolve.services.exports import CaseExportService
from zecsolve.services.grants import GrantService
from zecsolve.services.reports import CaseReportService
from zecsolve.services.resolutions import ResolutionService
from zecsolve.services.verifications import VerificationService
from zecsolve.services.workflow import WorkflowError

pytestmark = pytest.mark.postgres


def test_merchant_export_replays_current_claim_consent_and_exact_evidence(
    database, root, submissions
):
    evidence, claims, merchant, case, _, customer, request = submissions
    claim, _ = claims.submit(
        customer, case, claim_request(note=" \nPrivate business assertion é"), "claim"
    )
    stored, _ = evidence.submit(
        customer, case, request.model_copy(update={"claim_id": claim.submission_id}), "evidence"
    )
    adapter = VerifierAdapter(root / "target/debug/zecsolve-verifier")
    attempt, _ = VerificationService(database, evidence.cipher, adapter, evidence.slots).verify(
        merchant, case, CaseVerifyRequest(evidence_id=stored.evidence_id), "verify"
    )
    packet = CaseExportService(database, evidence.cipher, evidence.slots).export(merchant, case)
    assert packet.payload.replay_scope == "FULL_HISTORY"
    assert packet.payload.report.verifications == [attempt]
    assert packet.payload.evidence[0].receipt.text() == request.receipt_json
    assert packet.payload.evidence[0].raw_transaction_hex.text() == request.raw_tx_hex
    assert packet.payload.report.claims[0].note == " \nPrivate business assertion é"
    result = replay_packet(packet.model_dump_json().encode(), adapter)
    assert result.status == "REPRODUCED", result.model_dump_json()
    # Changing one byte is caught before replay; no service writes are performed.
    tampered = (
        packet.model_dump_json()
        .replace("Private business assertion", "Private business assertio!")
        .encode()
    )
    assert replay_packet(tampered, adapter).status == "FAILED"
    assert (
        CaseReportService(database).get(merchant, case).case.version
        == packet.payload.report.case.version
    )


def test_scoped_export_requires_separate_permission_and_omits_private_context(
    database, root, submissions
):
    evidence, claims, merchant, case, customer_grant, customer, request = submissions
    private, _ = claims.submit(customer, case, claim_request(note="PRIVATE_EXPORT_CANARY"), "claim")
    shared, _ = evidence.submit(
        customer,
        case,
        request.model_copy(
            update={"share_with_reviewers": True, "claim_id": private.submission_id}
        ),
        "shared",
    )
    hidden, _ = evidence.submit(customer, case, request, "hidden")
    adapter = VerifierAdapter(root / "target/debug/zecsolve-verifier")
    VerificationService(database, evidence.cipher, adapter, evidence.slots).verify(
        merchant, case, CaseVerifyRequest(evidence_id=shared.evidence_id), "verify"
    )
    _, denied = reviewer(database, merchant, case, SECTIONS, [shared.evidence_id])
    _, actor = reviewer(database, merchant, case, SECTIONS, [shared.evidence_id], True)
    service = CaseExportService(database, evidence.cipher, evidence.slots)
    for principal in (customer, denied):
        with pytest.raises(WorkflowError) as error:
            service.export(principal, case)
        assert error.value.status == 403
    packet = service.export(actor, case)
    assert packet.payload.replay_scope == "LIMITED"
    assert packet.payload.report == CaseReportService(database).get(actor, case).model_copy(
        update={"generated_at": packet.payload.report.generated_at}
    )
    assert packet.payload.evidence[0].receipt.text() == request.receipt_json
    assert packet.payload.evidence[0].submission_payload.availability == "OMITTED"
    serialized = packet.model_dump_json()
    for secret in (
        "PRIVATE_EXPORT_CANARY",
        str(private.submission_id),
        str(hidden.evidence_id),
        str(merchant.merchant_id),
        str(customer_grant.grant.grant_id),
        "actor_id",
        'payload_sha256": "' + shared.payload_sha256,
    ):
        assert secret not in serialized
    result = replay_packet(serialized.encode(), adapter)
    assert result.status == "LIMITED"
    assert any(check.code == "OUTPUT_RECOVERY_REPRODUCED" for check in result.checks)


@pytest.mark.parametrize("role", ["merchant", "reviewer"])
def test_revocation_during_export_decryption_prevents_disclosure(
    database, monkeypatch, submissions, role
):
    evidence, _, merchant, case, _, customer, request = submissions
    stored, _ = evidence.submit(
        customer, case, request.model_copy(update={"share_with_reviewers": True}), "upload"
    )
    granted, actor = reviewer(database, merchant, case, ["evidence"], [stored.evidence_id], True)
    original = evidence.cipher.decrypt

    def revoke(*args, **kwargs):
        result = original(*args, **kwargs)
        if role == "reviewer":
            GrantService(database).revoke(merchant, case, granted.grant.grant_id)
        else:
            with Session(database) as session, session.begin():
                revoke_credential(session, merchant.credential_id)
        return result

    monkeypatch.setattr(evidence.cipher, "decrypt", revoke)
    with pytest.raises(WorkflowError) as error:
        CaseExportService(database, evidence.cipher, evidence.slots).export(
            actor if role == "reviewer" else merchant, case
        )
    assert error.value.status == 401


def test_export_snapshot_does_not_mix_concurrent_approval(
    database, root, verification_setup, resolution_setup
):
    _, _, _, _, evidence = verification_setup
    merchant, case, attempt = resolution_setup
    triggered = threading.Event()
    thread = threading.local()

    def approve_concurrently():
        thread.writer = True
        return ResolutionService(database, SimulatedObserver(), simulated_authority).resolve(
            merchant, case.case_id, approve(attempt), "approve"
        )

    def after_select(connection, cursor, statement, parameters, context, executemany):
        if (
            not getattr(thread, "writer", False)
            and "FROM cases" in statement
            and not triggered.is_set()
        ):
            triggered.set()
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(approve_concurrently).result(timeout=10)

    event.listen(database, "after_cursor_execute", after_select)
    try:
        old = CaseExportService(database, evidence.cipher, evidence.slots).export(
            merchant, case.case_id
        )
    finally:
        event.remove(database, "after_cursor_execute", after_select)
    assert triggered.is_set()
    assert old.payload.report.case.version == 3
    assert old.payload.report.decisions == []
    assert old.payload.balance_context.approved_allocations == []
    assert old.payload.report.balances.credited_zat == 0
    latest = CaseExportService(database, evidence.cipher, evidence.slots).export(
        merchant, case.case_id
    )
    assert latest.payload.report.case.version == 4
    assert latest.payload.report.balances.credited_zat == 100_000
    assert (
        len(latest.payload.report.decisions)
        == len(latest.payload.balance_context.approved_allocations)
        == 1
    )
    adapter = VerifierAdapter(root / "target/debug/zecsolve-verifier")
    for packet in (old, latest):
        result = replay_packet(packet.model_dump_json().encode(), adapter)
        assert result.status == "REPRODUCED", result.model_dump_json()


@pytest.mark.parametrize("role", ["merchant", "foreign", "customer", "report", "evidence"])
def test_export_http_permission_matrix_and_download_contract(
    database, root, monkeypatch, submissions, role
):
    from zecsolve.auth.dependencies import require_actor

    evidence, _, merchant, case, customer_grant, customer, request = submissions
    stored, _ = evidence.submit(
        customer, case, request.model_copy(update={"share_with_reviewers": True}), "upload"
    )
    report_grant, _ = reviewer(database, merchant, case, ["case"], [], False)
    allowed_grant, _ = reviewer(database, merchant, case, ["evidence"], [stored.evidence_id], True)
    with Session(database) as session, session.begin():
        foreign = provision_merchant(session, "Foreign export merchant")
    monkeypatch.setattr("zecsolve.main.make_engine", lambda settings: database)
    app = create_app(
        Settings(
            _env_file=None,
            browser_origins=[ORIGIN],
            verifier_path=root / "target/debug/zecsolve-verifier",
            migrations_path=root / "apps/api/migrations",
        )
    )
    app.state.evidence_cipher = evidence.cipher
    if role == "merchant":
        app.dependency_overrides[require_actor] = lambda: merchant
    if role == "foreign":
        app.dependency_overrides[require_actor] = lambda: MerchantPrincipal(
            foreign.merchant_id, foreign.credential_id
        )
    with TestClient(app, base_url=ORIGIN) as api:
        if role in ("customer", "report", "evidence"):
            grant = {"customer": customer_grant, "report": report_grant, "evidence": allowed_grant}[
                role
            ]
            assert (
                api.post(
                    "/api/session", json={"code": grant.access_code}, headers={"Origin": ORIGIN}
                ).status_code
                == 201
            )
        response = api.get(f"/api/cases/{case}/export")
        assert (
            response.status_code
            == {"merchant": 200, "foreign": 404, "customer": 403, "report": 403, "evidence": 200}[
                role
            ]
        ), response.text
        if response.status_code == 200:
            assert response.headers["cache-control"] == "no-store"
            assert (
                response.headers["content-disposition"]
                == f'attachment; filename="zecsolve-{case}.json"'
            )
            parse_packet(response.content)
        if role == "evidence":
            assert api.get(f"/api/cases/{uuid.uuid4()}/export").status_code == 404
            GrantService(database).revoke(merchant, case, grant.grant.grant_id)
            assert api.get(f"/api/cases/{case}/export").status_code == 401


def test_case_only_export_excludes_all_originals_and_expired_access(database, submissions):
    from datetime import timedelta

    from sqlalchemy import func, select
    from zecsolve.auth.access import GrantPrincipal
    from zecsolve.db.models import CaseGrant
    from zecsolve.schemas.access import GrantScopeV1

    evidence, _, merchant, case, _, customer, request = submissions
    hidden, _ = evidence.submit(customer, case, request, "hidden")
    _, actor = reviewer(database, merchant, case, ["case"], [], True)
    packet = CaseExportService(database, evidence.cipher, evidence.slots).export(actor, case)
    assert packet.payload.evidence == []
    assert packet.payload.report.evidence is None
    assert str(hidden.evidence_id) not in packet.model_dump_json()
    assert request.receipt_json not in packet.model_dump_json()
    with Session(database) as session, session.begin():
        now = session.scalar(select(func.clock_timestamp()))
        grant = CaseGrant(
            id=uuid.uuid4(),
            merchant_id=merchant.merchant_id,
            case_id=case,
            issued_by=merchant.credential_id,
            role="reviewer",
            scope=GrantScopeV1(
                role="reviewer", report_sections=["case"], allow_export=True
            ).model_dump(mode="json"),
            token_sha256=uuid.uuid4().hex * 2,
            created_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
        )
        session.add(grant)
        expired = GrantPrincipal(merchant.merchant_id, case, grant.id, "reviewer")
    with pytest.raises(WorkflowError) as error:
        CaseExportService(database, evidence.cipher, evidence.slots).export(expired, case)
    assert error.value.status == 401


def test_browser_logout_during_decryption_blocks_export(database, monkeypatch, submissions):
    from zecsolve.services.sessions import SessionService

    evidence, _, merchant, case, _, customer, request = submissions
    stored, _ = evidence.submit(
        customer, case, request.model_copy(update={"share_with_reviewers": True}), "shared"
    )
    granted, _ = reviewer(database, merchant, case, ["evidence"], [stored.evidence_id], True)
    sessions = SessionService(database)
    issued = sessions.exchange(granted.access_code)
    actor, _, _ = sessions.authenticate(issued.token)
    decrypt = evidence.cipher.decrypt

    def logout(*args, **kwargs):
        result = decrypt(*args, **kwargs)
        sessions.logout(issued.token)
        return result

    monkeypatch.setattr(evidence.cipher, "decrypt", logout)
    with pytest.raises(WorkflowError) as error:
        CaseExportService(database, evidence.cipher, evidence.slots).export(actor, case)
    assert error.value.status == 401


def test_foreign_allocation_export_is_opaque_and_replays(database, root, submissions):
    from sqlalchemy import insert
    from test_postgres import allocation, seed
    from zecsolve.db.models import OutputAllocation

    evidence, _, merchant, case, _, customer, request = submissions
    stored, _ = evidence.submit(customer, case, request, "evidence")
    adapter = VerifierAdapter(root / "target/debug/zecsolve-verifier")
    attempt, _ = VerificationService(database, evidence.cipher, adapter, evidence.slots).verify(
        merchant, case, CaseVerifyRequest(evidence_id=stored.evidence_id), "verify"
    )
    foreign = seed(database)[0]
    record = allocation(foreign)
    record.update(txid=attempt.result.output.txid, output_index=attempt.result.output.output_index)
    with database.begin() as connection:
        connection.execute(insert(OutputAllocation).values(**record))
    packet = CaseExportService(database, evidence.cipher, evidence.slots).export(merchant, case)
    assert packet.payload.balance_context.foreign_conflict
    assert packet.payload.balance_context.approved_allocations == []
    assert str(foreign["invoice_id"]) not in packet.model_dump_json()
    result = replay_packet(packet.model_dump_json().encode(), adapter)
    assert result.status == "REPRODUCED", result.model_dump_json()
    assert "ALLOCATION_AND_SOURCE_AUTHORITY_ARE_EXTERNAL_ASSERTIONS" in result.external_assertions


def test_export_size_limit_fails_before_decryption(database, monkeypatch, submissions):
    evidence, _, merchant, case, _, customer, request = submissions
    evidence.submit(customer, case, request, "evidence")
    monkeypatch.setattr("zecsolve.services.exports.MAX_PACKET_BYTES", 1)

    def forbidden(*args, **kwargs):
        pytest.fail("Oversized export reached decryption")

    monkeypatch.setattr(evidence.cipher, "decrypt", forbidden)
    with pytest.raises(WorkflowError) as error:
        CaseExportService(database, evidence.cipher, evidence.slots).export(merchant, case)
    assert error.value.status == 413


@pytest.mark.parametrize("value", [None, ""])
def test_export_preserves_missing_and_empty_inputs_in_negative_replay(
    database, root, submissions, value
):
    evidence, _, merchant, case, _, customer, request = submissions
    stored, _ = evidence.submit(
        customer,
        case,
        request.model_copy(update={"receipt_json": value, "raw_tx_hex": value}),
        "missing",
    )
    adapter = VerifierAdapter(root / "target/debug/zecsolve-verifier")
    VerificationService(database, evidence.cipher, adapter, evidence.slots).verify(
        merchant, case, CaseVerifyRequest(evidence_id=stored.evidence_id), "verify"
    )
    packet = CaseExportService(database, evidence.cipher, evidence.slots).export(merchant, case)
    inputs = packet.payload.evidence[0]
    assert inputs.receipt.text() == inputs.raw_transaction_hex.text() == value
    assert inputs.receipt.availability == ("NOT_SUBMITTED" if value is None else "PRESENT")
    result = replay_packet(packet.model_dump_json().encode(), adapter)
    assert result.status == "REPRODUCED", result.model_dump_json()
    assert any(check.code == "NEGATIVE_RESULT_REPRODUCED" for check in result.checks)
