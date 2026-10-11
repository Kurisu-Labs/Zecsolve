import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from test_evidence_service import evidence_setup as evidence_setup
from zecsolve.adapters.verifier import VerifierAdapter
from zecsolve.auth.access import GrantPrincipal
from zecsolve.auth.credentials import MerchantPrincipal, provision_merchant
from zecsolve.config import Settings
from zecsolve.db.models import (
    AccessSubmissionRequest,
    Case,
    CaseEvent,
    Claim,
    Evidence,
    EvidenceConsent,
    EvidenceContent,
    OutputAllocation,
    Verification,
)
from zecsolve.main import create_app
from zecsolve.schemas.evidence import EvidenceSubmitRequestV2
from zecsolve.schemas.grant import GrantCreateRequest
from zecsolve.schemas.submission import ClaimSubmitRequest
from zecsolve.schemas.workflow_verification import CaseVerifyRequest
from zecsolve.services.audit import load_event_chain
from zecsolve.services.claims import ClaimService
from zecsolve.services.grants import GrantService
from zecsolve.services.reports import CaseReportService
from zecsolve.services.sessions import SessionService
from zecsolve.services.verifications import VerificationService
from zecsolve.services.workflow import WorkflowError

pytestmark = pytest.mark.postgres
ORIGIN = "https://app.example"


def claim_request(**changes):
    return ClaimSubmitRequest.model_validate(
        {
            "note": "<b>Reported missing payment</b>",
            "processing_authorized": True,
            "disclosure_version": "claim-disclosure-v1",
            **changes,
        }
    )


@pytest.fixture
def submissions(database, evidence_setup):
    evidence, merchant, case, legacy = evidence_setup
    granted, _ = GrantService(database).create(
        merchant, case.case_id, GrantCreateRequest(scope={"role": "customer"}), "customer"
    )
    actor = GrantPrincipal(merchant.merchant_id, case.case_id, granted.grant.grant_id, "customer")
    request = EvidenceSubmitRequestV2.model_validate(
        {
            **legacy.model_dump(),
            "disclosure_version": "evidence-disclosure-v2",
            "source_kind": "customer_submission",
        }
    )
    return evidence, ClaimService(database), merchant, case.case_id, granted, actor, request


def counts(database):
    with Session(database) as session:
        return [
            session.scalar(select(func.count()).select_from(model))
            for model in (
                Claim,
                Evidence,
                EvidenceContent,
                EvidenceConsent,
                AccessSubmissionRequest,
                CaseEvent,
                Verification,
                OutputAllocation,
            )
        ]


def test_customer_claim_evidence_consent_attribution_and_exact_bytes(database, submissions):
    evidence, claims, merchant, case, granted, actor, request = submissions
    claim, replayed = claims.submit(actor, case, claim_request(), "claim")
    assert not replayed
    request = request.model_copy(
        update={
            "claim_id": claim.submission_id,
            "receipt_json": " \n{}\n",
            "raw_tx_hex": "",
            "share_with_reviewers": True,
        }
    )
    stored, replayed = evidence.submit(actor, case, request, "evidence")
    assert not replayed and stored.schema_version == "2"
    assert stored.submitted_by is None and stored.actor_grant_id == granted.grant.grant_id
    assert stored.case_state == "AWAITING_EVIDENCE" and stored.claim_id == claim.submission_id
    assert evidence.read_content(merchant, case, stored.evidence_id) == request
    with Session(database) as session:
        row = session.get(Claim, claim.submission_id)
        assert (row.claimant_role, row.actor_credential_id, row.actor_grant_id) == (
            "customer",
            None,
            actor.grant_id,
        )
        consent = session.get(EvidenceConsent, stored.consent_id)
        assert consent.processing_authorized and consent.share_with_reviewers
        assert consent.grant_id == actor.grant_id and consent.credential_id is None
        history = load_event_chain(session, session.get(Case, case))
        assert [item.schema_version for item in history] == ["1", "2", "2"]
        assert history[1].payload["share_with_reviewers"] is False
        assert history[2].payload["consent_id"] == str(consent.id)
        assert row.note not in str(history[1].payload)
        assert (
            session.get(EvidenceContent, stored.evidence_id).ciphertext
            != request.receipt_json.encode()
        )
    assert counts(database) == [1, 1, 1, 1, 2, 3, 0, 0]
    assert claims.submit(actor, case, claim_request(), "claim") == (claim, True)
    assert evidence.submit(actor, case, request, "evidence") == (stored, True)
    with pytest.raises(WorkflowError, match="IDEMPOTENCY_CONFLICT"):
        claims.submit(actor, case, claim_request(note="changed"), "claim")
    with pytest.raises(WorkflowError, match="IDEMPOTENCY_CONFLICT"):
        evidence.submit(
            actor, case, request.model_copy(update={"share_with_reviewers": False}), "evidence"
        )
    assert counts(database) == [1, 1, 1, 1, 2, 3, 0, 0]


def test_customer_evidence_can_be_verified_and_reported_by_merchant(database, root, submissions):
    evidence, claims, merchant, case, _, actor, request = submissions
    claims.submit(actor, case, claim_request(reported_txid="ab" * 32), "claim")
    stored, _ = evidence.submit(actor, case, request, "evidence")
    service = VerificationService(
        database,
        evidence.cipher,
        VerifierAdapter(root / "target/debug/zecsolve-verifier"),
        evidence.slots,
    )
    attempt, _ = service.verify(
        merchant, case, CaseVerifyRequest(evidence_id=stored.evidence_id), "verify"
    )
    assert attempt.result.receipt_state == "VALID"
    report = CaseReportService(database).get(merchant, case)
    assert report.evidence[0] == stored and report.claims[0].claimant_role == "customer"
    assert report.events[-1].action == "VERIFICATION_RECORDED"
    assert report.balances.credited_zat == 0
    for operation in (
        lambda: service.verify(
            actor, case, CaseVerifyRequest(evidence_id=stored.evidence_id), "denied"
        ),
        lambda: CaseReportService(database).get(actor, case),
        lambda: evidence.get(actor, case, stored.evidence_id),
        lambda: evidence.read_content(actor, case, stored.evidence_id),
    ):
        with pytest.raises(WorkflowError) as error:
            operation()
        assert error.value.status == 403


@pytest.mark.parametrize("operation", ["claim", "evidence"])
@pytest.mark.parametrize("same_key", [True, False])
def test_concurrent_customer_submissions_and_retry_scope(
    database, submissions, operation, same_key
):
    evidence, claims, _, case, _, actor, request = submissions
    barrier = threading.Barrier(2)

    def submit(index):
        barrier.wait(timeout=5)
        return (claims if operation == "claim" else evidence).submit(
            actor,
            case,
            claim_request() if operation == "claim" else request,
            "shared" if same_key else str(index),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(submit, [0, 1]))
    expected = 1 if same_key else 2
    if same_key:
        assert results[0][0] == results[1][0]
        assert sorted(result[1] for result in results) == [False, True]
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(AccessSubmissionRequest)) == expected
        current = session.get(Case, case)
        assert current.version == expected + 1
        load_event_chain(session, current)


def test_same_keys_are_separate_per_actor_and_operation_and_claim_links_are_scoped(
    database, submissions
):
    evidence, claims, merchant, case, _, actor, request = submissions
    other_grant, _ = GrantService(database).create(
        merchant, case, GrantCreateRequest(scope={"role": "customer"}), "second"
    )
    other = GrantPrincipal(merchant.merchant_id, case, other_grant.grant.grant_id, "customer")
    first, _ = claims.submit(actor, case, claim_request(), "shared")
    second, _ = claims.submit(other, case, claim_request(), "shared")
    assert first.submission_id != second.submission_id
    for claim_id in (second.submission_id, uuid.uuid4()):
        with pytest.raises(WorkflowError) as error:
            evidence.submit(
                actor, case, request.model_copy(update={"claim_id": claim_id}), "shared"
            )
        assert error.value.status == 404
    stored, _ = evidence.submit(
        actor, case, request.model_copy(update={"claim_id": first.submission_id}), "shared"
    )
    merchant_claim, _ = claims.submit(merchant, case, claim_request(), "shared")
    merchant_evidence, _ = evidence.submit(merchant, case, request, "shared")
    assert (
        merchant_evidence.submitted_by == merchant.credential_id
        and merchant_evidence.actor_grant_id is None
    )
    assert merchant_claim.submission_id not in (first.submission_id, second.submission_id)
    assert stored.evidence_id != merchant_evidence.evidence_id
    with Session(database) as session:
        consent = session.get(EvidenceConsent, merchant_evidence.consent_id)
        assert consent.credential_id == merchant.credential_id and not consent.share_with_reviewers
    # Changing the API request version does not create a second merchant retry namespace.
    from zecsolve.schemas.evidence import EvidenceSubmitRequest

    legacy = EvidenceSubmitRequest(source="old", processing_authorized=True)
    with pytest.raises(WorkflowError, match="IDEMPOTENCY_CONFLICT"):
        evidence.submit(merchant, case, legacy, "shared")
    evidence.submit(merchant, case, legacy, "old-key")
    with pytest.raises(WorkflowError, match="IDEMPOTENCY_CONFLICT"):
        evidence.submit(merchant, case, request, "old-key")


@pytest.mark.parametrize("operation", ["claim", "evidence"])
def test_terminal_cases_allow_only_authorized_completed_retries(database, submissions, operation):
    evidence, claims, _, case, _, actor, request = submissions
    service, body = (claims, claim_request()) if operation == "claim" else (evidence, request)
    accepted, _ = service.submit(actor, case, body, "first")
    with database.begin() as connection:
        connection.execute(update(Case).where(Case.id == case).values(state="RESOLVED"))
    assert service.submit(actor, case, body, "first") == (accepted, True)
    with pytest.raises(WorkflowError, match="CASE_TERMINAL"):
        service.submit(actor, case, body, "new")


@pytest.mark.parametrize("operation", ["claim", "evidence"])
def test_deferred_commit_failure_rolls_back_entire_submission(database, submissions, operation):
    evidence, claims, _, case, _, actor, request = submissions
    before = counts(database)
    with database.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION fail_submission() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'test rollback'; END; $$"
            )
        )
        connection.execute(
            text(
                "CREATE CONSTRAINT TRIGGER fail_submission AFTER INSERT ON "
                "access_submission_requests DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
                "EXECUTE FUNCTION fail_submission()"
            )
        )
    service, body = (claims, claim_request()) if operation == "claim" else (evidence, request)
    with pytest.raises(SQLAlchemyError):
        service.submit(actor, case, body, "failed")
    assert counts(database) == before
    with Session(database) as session:
        assert session.get(Case, case).version == 1


@pytest.mark.parametrize("revoke", ["grant", "session"])
def test_revocation_during_encryption_prevents_persistence(database, submissions, revoke):
    evidence, _, merchant, case, granted, _, request = submissions
    sessions = SessionService(database)
    issued = sessions.exchange(granted.access_code)
    actor = sessions.authenticate(issued.token)[0]
    encrypt = evidence.cipher.encrypt

    def revoke_then_encrypt(*args, **kwargs):
        if revoke == "grant":
            GrantService(database).revoke(merchant, case, actor.grant_id)
        else:
            sessions.logout(issued.token)
        return encrypt(*args, **kwargs)

    evidence.cipher.encrypt = revoke_then_encrypt
    with pytest.raises(WorkflowError) as error:
        evidence.submit(actor, case, request, "revoked")
    assert error.value.status == 401
    assert counts(database) == [0, 0, 0, 0, 0, 1, 0, 0]


def test_reviewer_foreign_case_and_foreign_merchant_cannot_submit(database, submissions):
    evidence, claims, merchant, case, _, actor, request = submissions
    review, _ = GrantService(database).create(
        merchant,
        case,
        GrantCreateRequest(scope={"role": "reviewer", "report_sections": ["case"]}),
        "review",
    )
    reviewer = GrantPrincipal(merchant.merchant_id, case, review.grant.grant_id, "reviewer")
    with Session(database) as session, session.begin():
        other = provision_merchant(session, "Foreign merchant")
    foreign = MerchantPrincipal(other.merchant_id, other.credential_id)
    for principal, target, expected in (
        (reviewer, case, 403),
        (foreign, case, 404),
        (actor, uuid.uuid4(), 404),
    ):
        for service, body in ((claims, claim_request()), (evidence, request)):
            with pytest.raises(WorkflowError) as error:
                service.submit(principal, target, body, "forbidden")
            assert error.value.status == expected
    assert counts(database) == [0, 0, 0, 0, 0, 1, 0, 0]


def test_customer_cookie_api_minimal_responses_csrf_retries_and_role_boundaries(
    database, root, monkeypatch, submissions
):
    evidence, _, merchant, case, granted, _, request = submissions
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
    with TestClient(app, base_url=ORIGIN) as api:
        login = api.post(
            "/api/session", json={"code": granted.access_code}, headers={"Origin": ORIGIN}
        )
        assert login.status_code == 201
        headers = {
            "Origin": ORIGIN,
            "X-CSRF-Token": api.cookies.get("__Host-zecsolve_csrf"),
            "Idempotency-Key": "same",
        }
        for name, body in (
            ("claims", claim_request().model_dump(mode="json")),
            ("evidence", request.model_dump(mode="json")),
        ):
            path = f"/api/cases/{case}/{name}"
            assert api.post(path, json=body).status_code == 403
            accepted = api.post(path, json=body, headers=headers)
            assert accepted.status_code == 201, accepted.text
            assert set(accepted.json()) == {
                "schema_version",
                "status",
                "operation",
                "submission_id",
                "accepted_at",
            }
            assert (
                accepted.headers["cache-control"] == "no-store"
                and "location" not in accepted.headers
            )
            retry = api.post(path, json=body, headers=headers)
            assert retry.status_code == 200 and retry.json() == accepted.json()
            assert retry.headers["idempotency-replayed"] == "true"
        for method, path in (
            ("GET", "/api/cases"),
            ("GET", f"/api/cases/{case}"),
            ("GET", f"/api/cases/{case}/report"),
            ("GET", f"/api/cases/{case}/evidence/{accepted.json()['submission_id']}"),
            ("POST", f"/api/cases/{case}/verify"),
            ("POST", f"/api/cases/{case}/resolve"),
            ("POST", f"/api/cases/{case}/grants"),
        ):
            assert api.request(method, path, headers=headers).status_code == 403
        legacy = {"source": "old", "processing_authorized": True}
        assert (
            api.post(f"/api/cases/{case}/evidence", json=legacy, headers=headers).status_code == 422
        )
        # A fresh session for the same grant recovers the prior safe acknowledgement.
        assert (
            api.post(
                "/api/session", json={"code": granted.access_code}, headers={"Origin": ORIGIN}
            ).status_code
            == 201
        )
        headers["X-CSRF-Token"] = api.cookies.get("__Host-zecsolve_csrf")
        restored = api.post(
            f"/api/cases/{case}/evidence", json=request.model_dump(mode="json"), headers=headers
        )
        assert restored.status_code == 200 and restored.json() == accepted.json()
        GrantService(database).revoke(merchant, case, granted.grant.grant_id)
        assert (
            api.post(
                f"/api/cases/{case}/claims",
                json=claim_request().model_dump(mode="json"),
                headers=headers,
            ).status_code
            == 401
        )


@pytest.mark.parametrize("sharing", [False, True])
def test_only_explicit_evidence_consent_enables_reviewer_selection(database, submissions, sharing):
    evidence, _, merchant, case, _, actor, request = submissions
    stored, _ = evidence.submit(
        actor, case, request.model_copy(update={"share_with_reviewers": sharing}), "evidence"
    )
    grant_request = GrantCreateRequest(
        scope={
            "role": "reviewer",
            "report_sections": ["evidence"],
            "evidence_ids": [stored.evidence_id],
        }
    )
    if sharing:
        created, _ = GrantService(database).create(merchant, case, grant_request, "review")
        assert created.grant.scope.evidence_ids == [stored.evidence_id]
    else:
        with pytest.raises(WorkflowError):
            GrantService(database).create(merchant, case, grant_request, "review")


@pytest.mark.parametrize("operation", ["claim", "evidence"])
def test_expiry_after_case_lock_wait_prevents_commit(database, submissions, operation):
    from datetime import timedelta

    from sqlalchemy import event
    from zecsolve.db.models import CaseGrant
    from zecsolve.schemas.access import GrantScopeV1

    evidence, claims, merchant, case, _, _, request = submissions
    with Session(database) as session, session.begin():
        now = session.scalar(select(func.clock_timestamp()))
        grant = CaseGrant(
            id=uuid.uuid4(),
            merchant_id=merchant.merchant_id,
            case_id=case,
            issued_by=merchant.credential_id,
            role="customer",
            scope=GrantScopeV1(role="customer").model_dump(mode="json"),
            token_sha256=uuid.uuid4().hex * 2,
            created_at=now,
            expires_at=now + timedelta(seconds=1),
        )
        session.add(grant)
        actor = GrantPrincipal(merchant.merchant_id, case, grant.id, "customer")
    waiting = threading.Event()
    worker = threading.local()

    def reached_lock(connection, cursor, statement, parameters, context, executemany):
        if (
            getattr(worker, "writer", False)
            and "FROM cases" in statement
            and "FOR UPDATE" in statement
        ):
            waiting.set()

    def submit():
        worker.writer = True
        service, body = (claims, claim_request()) if operation == "claim" else (evidence, request)
        return service.submit(actor, case, body, "expires")

    event.listen(database, "before_cursor_execute", reached_lock)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            with database.begin() as lock:
                lock.execute(select(Case).where(Case.id == case).with_for_update())
                future = executor.submit(submit)
                assert waiting.wait(timeout=5)
                lock.execute(text("SELECT pg_sleep(1.1)"))
            with pytest.raises(WorkflowError) as error:
                future.result(timeout=5)
            assert error.value.status == 401
    finally:
        event.remove(database, "before_cursor_execute", reached_lock)
    assert counts(database) == [0, 0, 0, 0, 0, 1, 0, 0]


def test_merchant_report_rejects_claim_content_changed_outside_the_writer(database, submissions):
    _, claims, merchant, case, _, actor, _ = submissions
    claim, _ = claims.submit(actor, case, claim_request(), "claim")
    with database.begin() as connection:
        connection.execute(
            update(Claim).where(Claim.id == claim.submission_id).values(note="rewritten claim")
        )
    with pytest.raises(WorkflowError, match="CLAIM_CONTEXT_UNAVAILABLE"):
        CaseReportService(database).get(merchant, case)
