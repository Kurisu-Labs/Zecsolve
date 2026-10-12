import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_customer_submissions import ORIGIN, claim_request
from test_customer_submissions import submissions as submissions
from test_evidence_service import evidence_setup as evidence_setup
from zecsolve.adapters.verifier import VerifierAdapter
from zecsolve.auth.access import GrantPrincipal
from zecsolve.auth.credentials import MerchantPrincipal, provision_merchant
from zecsolve.config import Settings
from zecsolve.db.models import CaseGrant
from zecsolve.main import create_app
from zecsolve.schemas.access import GrantScopeV1
from zecsolve.schemas.disclosure import ReviewerReportV1
from zecsolve.schemas.grant import GrantCreateRequest
from zecsolve.schemas.workflow_verification import CaseVerifyRequest
from zecsolve.services.grants import GrantService
from zecsolve.services.reports import CaseReportService
from zecsolve.services.verifications import VerificationService
from zecsolve.services.workflow import WorkflowError

pytestmark = pytest.mark.postgres
SECTIONS = [
    "case",
    "invoice",
    "claims",
    "evidence",
    "verifications",
    "observations",
    "evaluations",
    "balances",
    "decisions",
    "events",
]


def reviewer(database, merchant, case, sections, evidence_ids=(), export=False):
    granted, _ = GrantService(database).create(
        merchant,
        case,
        GrantCreateRequest(
            scope={
                "role": "reviewer",
                "report_sections": sections,
                "evidence_ids": list(evidence_ids),
                "allow_export": export,
            }
        ),
        str(uuid.uuid4()),
    )
    return granted, GrantPrincipal(merchant.merchant_id, case, granted.grant.grant_id, "reviewer")


def test_selected_sections_claim_consent_and_no_nested_private_snapshots(
    database, root, submissions
):
    evidence, claims, merchant, case, _, customer, request = submissions
    private, _ = claims.submit(
        customer, case, claim_request(note="PRIVATE_CLAIM_CANARY"), "private"
    )
    shared, _ = claims.submit(customer, case, claim_request(share_with_reviewers=True), "shared")
    chosen, _ = evidence.submit(
        customer,
        case,
        request.model_copy(
            update={
                "share_with_reviewers": True,
                "claim_id": private.submission_id,
            }
        ),
        "chosen",
    )
    other, _ = evidence.submit(
        customer, case, request.model_copy(update={"share_with_reviewers": True}), "other"
    )
    hidden, _ = evidence.submit(customer, case, request, "hidden")
    verifier = VerificationService(
        database,
        evidence.cipher,
        VerifierAdapter(root / "target/debug/zecsolve-verifier"),
        evidence.slots,
    )
    attempt, _ = verifier.verify(
        merchant, case, CaseVerifyRequest(evidence_id=chosen.evidence_id), "chosen"
    )
    unselected, _ = verifier.verify(
        merchant, case, CaseVerifyRequest(evidence_id=other.evidence_id), "other"
    )
    _, actor = reviewer(database, merchant, case, SECTIONS, [chosen.evidence_id], True)
    report = CaseReportService(database).get(actor, case)
    assert isinstance(report, ReviewerReportV1)
    assert report.sections == SECTIONS
    assert [item.claim_id for item in report.claims] == [shared.submission_id]
    assert [item.evidence_id for item in report.evidence] == [chosen.evidence_id]
    assert [item.verification_id for item in report.verifications] == [attempt.verification_id]
    assert [item.verification_id for item in report.observations] == [attempt.verification_id]
    assert report.evaluations[0].result == attempt.evaluation.result
    assert report.balances == attempt.evaluation.result
    serialized = report.model_dump_json()
    for secret in (
        str(merchant.merchant_id),
        str(customer.grant_id),
        str(private.submission_id),
        "PRIVATE_CLAIM_CANARY",
        str(other.evidence_id),
        str(hidden.evidence_id),
        str(unselected.verification_id),
        "approved_allocations",
        "snapshot_hash",
        "previous_hash",
        "event_hash",
        "actor_id",
    ):
        assert secret not in serialized
    assert evidence.get(actor, case, chosen.evidence_id) == report.evidence[0]
    assert evidence.read_content(actor, case, chosen.evidence_id).claim_id == private.submission_id
    for evidence_id in (other.evidence_id, hidden.evidence_id, uuid.uuid4()):
        for operation in (evidence.get, evidence.read_content):
            with pytest.raises(WorkflowError) as error:
                operation(actor, case, evidence_id)
            assert error.value.status == 403
    with pytest.raises(WorkflowError) as error:
        CaseReportService(database).get(actor, case, unselected.verification_id)
    assert error.value.status == 404
    full = CaseReportService(database).get(merchant, case)
    assert len(full.evidence) == 3 and len(full.verifications) == 2 and len(full.claims) == 2
    assert full.schema_version == "1"


def test_report_only_projection_and_reauthorization_after_decryption(
    database, monkeypatch, submissions
):
    evidence, _, merchant, case, _, customer, request = submissions
    stored, _ = evidence.submit(
        customer, case, request.model_copy(update={"share_with_reviewers": True}), "upload"
    )
    _, limited = reviewer(database, merchant, case, ["case"])
    report = CaseReportService(database).get(limited, case)
    assert report.case is not None and report.invoice is None and report.evidence is None
    with pytest.raises(WorkflowError) as error:
        evidence.read_content(limited, case, stored.evidence_id)
    assert error.value.status == 403
    granted, actor = reviewer(database, merchant, case, ["evidence"], [stored.evidence_id])
    decrypt = evidence.cipher.decrypt

    def revoke_during_decrypt(*args, **kwargs):
        result = decrypt(*args, **kwargs)
        GrantService(database).revoke(merchant, case, granted.grant.grant_id)
        return result

    monkeypatch.setattr(evidence.cipher, "decrypt", revoke_during_decrypt)
    with pytest.raises(WorkflowError) as error:
        evidence.read_content(actor, case, stored.evidence_id)
    assert error.value.status == 401
    with pytest.raises(WorkflowError) as error:
        CaseReportService(database).get(actor, case)
    assert error.value.status == 401


def test_expired_reviewer_cannot_read(database, submissions):
    _, _, merchant, case, _, _, _ = submissions
    with Session(database) as session, session.begin():
        now = session.scalar(select(func.clock_timestamp()))
        grant = CaseGrant(
            id=uuid.uuid4(),
            merchant_id=merchant.merchant_id,
            case_id=case,
            issued_by=merchant.credential_id,
            role="reviewer",
            scope=GrantScopeV1(role="reviewer", report_sections=["case"]).model_dump(mode="json"),
            token_sha256=uuid.uuid4().hex * 2,
            created_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
        )
        session.add(grant)
        actor = GrantPrincipal(merchant.merchant_id, case, grant.id, "reviewer")
    with pytest.raises(WorkflowError) as error:
        CaseReportService(database).get(actor, case)
    assert error.value.status == 401


@pytest.mark.parametrize("role", ["merchant", "foreign", "customer", "report", "evidence"])
def test_route_role_matrix_and_exact_component_response(
    database, root, monkeypatch, submissions, role
):
    evidence, claims, merchant, case, customer_grant, customer, request = submissions
    private, _ = claims.submit(customer, case, claim_request(), "private")
    request = request.model_copy(
        update={
            "receipt_json": ' \n{"note":"é"}\n',
            "raw_tx_hex": "",
            "share_with_reviewers": True,
            "claim_id": private.submission_id,
        }
    )
    stored, _ = evidence.submit(customer, case, request, "upload")
    report_grant, _ = reviewer(database, merchant, case, ["case", "claims"])
    evidence_grant, _ = reviewer(database, merchant, case, ["evidence"], [stored.evidence_id], True)
    with Session(database) as session, session.begin():
        issued = provision_merchant(session, "Foreign merchant")
    # Merchant credentials are deliberately not recoverable: use the auth dependency
    # for merchant principals; exercise real browser exchange for every grant role.
    from zecsolve.auth.dependencies import require_actor, require_merchant

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
    if role in ("merchant", "foreign"):
        principal = (
            merchant
            if role == "merchant"
            else MerchantPrincipal(issued.merchant_id, issued.credential_id)
        )
        app.dependency_overrides[require_actor] = lambda: principal
        app.dependency_overrides[require_merchant] = lambda: principal
    with TestClient(app, base_url=ORIGIN) as api:
        if role not in ("merchant", "foreign"):
            grant = {
                "customer": customer_grant,
                "report": report_grant,
                "evidence": evidence_grant,
            }[role]
            assert (
                api.post(
                    "/api/session", json={"code": grant.access_code}, headers={"Origin": ORIGIN}
                ).status_code
                == 201
            )
        headers = {
            "Origin": ORIGIN,
            "X-CSRF-Token": api.cookies.get("__Host-zecsolve_csrf", ""),
            "Idempotency-Key": "denied",
        }
        report = api.get(f"/api/cases/{case}/report")
        assert (
            report.status_code
            == {"merchant": 200, "foreign": 404, "customer": 403, "report": 200, "evidence": 200}[
                role
            ]
        ), report.text
        if role in ("report", "evidence"):
            ReviewerReportV1.model_validate(report.json())
            assert "invoice" not in report.json()
            assert str(merchant.merchant_id) not in report.text
        for suffix in ("", "/content"):
            response = api.get(f"/api/cases/{case}/evidence/{stored.evidence_id}{suffix}")
            assert (
                response.status_code
                == {
                    "merchant": 200,
                    "foreign": 404,
                    "customer": 403,
                    "report": 403,
                    "evidence": 200,
                }[role]
            ), response.text
            if suffix and response.status_code == 200:
                assert response.json() == {
                    "schema_version": "evidence-content-v1",
                    "evidence_id": str(stored.evidence_id),
                    "receipt_json": request.receipt_json,
                    "raw_tx_hex": "",
                }
                assert str(private.submission_id) not in response.text
        if role in ("report", "evidence", "customer"):
            for method, path in [
                ("GET", "/api/cases"),
                ("GET", f"/api/cases/{case}"),
                ("POST", f"/api/cases/{case}/verify"),
                ("POST", f"/api/cases/{case}/resolve"),
                ("POST", f"/api/cases/{case}/grants"),
                ("POST", f"/api/cases/{case}/chain-observations"),
            ]:
                response = api.request(method, path, headers=headers)
                assert response.status_code == 403, (path, response.text)
        if role in ("report", "evidence"):
            for path, body in [
                ("claims", claim_request().model_dump(mode="json")),
                ("evidence", request.model_dump(mode="json")),
            ]:
                assert (
                    api.post(f"/api/cases/{case}/{path}", json=body, headers=headers).status_code
                    == 403
                )
            assert api.get(f"/api/cases/{uuid.uuid4()}/report").status_code == 404
            GrantService(database).revoke(merchant, case, grant.grant.grant_id)
            assert api.get(f"/api/cases/{case}/report").status_code == 401
