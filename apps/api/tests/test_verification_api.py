import base64
import json
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from zecsolve.auth.credentials import provision_merchant
from zecsolve.config import Settings
from zecsolve.main import create_app

pytestmark = pytest.mark.postgres


@pytest.fixture
def verification_api(database, root, receipt, raw_tx, monkeypatch):
    monkeypatch.setattr("zecsolve.main.make_engine", lambda settings: database)
    app = create_app(
        Settings(
            _env_file=None,
            verifier_path=root / "target/debug/zecsolve-verifier",
            migrations_path=root / "apps/api/migrations",
            evidence_key_id="test",
            evidence_key=base64.b64encode(os.urandom(32)).decode(),
        )
    )
    with Session(database) as session, session.begin():
        merchant = provision_merchant(session, "HTTP verification")
    headers = {"Authorization": "Bearer " + merchant.token, "Idempotency-Key": "demo"}
    with TestClient(app) as api:
        manifest = json.loads((root / "fixtures/manifest.json").read_text())["expected"]
        invoice = api.post(
            "/api/invoices",
            headers=headers,
            json={
                "expected_zat": 200_000,
                "network": "mainnet",
                "pool": "orchard",
                "receiver_address": manifest["receiver_address"],
                "expected_memo": manifest["memo_text"],
            },
        )
        assert invoice.status_code == 201
        case = api.post(
            "/api/cases", headers=headers, json={"invoice_id": invoice.json()["invoice_id"]}
        )
        assert case.status_code == 201
        case_id = case.json()["case_id"]
        evidence = api.post(
            f"/api/cases/{case_id}/evidence",
            headers=headers,
            json={
                "receipt_json": receipt,
                "raw_tx_hex": raw_tx,
                "source": "public fixture",
                "processing_authorized": True,
            },
        )
        assert evidence.status_code == 201
        yield api, headers, case_id, evidence.json()["evidence_id"]


def test_authenticated_invoice_to_evidence_verification_and_report(verification_api):
    api, headers, case, evidence = verification_api
    response = api.post(
        f"/api/cases/{case}/verify", headers=headers, json={"evidence_id": evidence}
    )
    assert response.status_code == 201
    attempt = response.json()
    assert (
        attempt["result"]["receipt_state"] == "VALID"
        and attempt["observation"]["state"] == "UNAVAILABLE"
    )
    replay = api.post(f"/api/cases/{case}/verify", headers=headers, json={"evidence_id": evidence})
    assert replay.status_code == 200 and replay.json() == attempt
    report = api.get(f"/api/cases/{case}/report", headers=headers)
    assert report.status_code == 200 and report.headers["cache-control"] == "no-store"
    body = report.json()
    assert body["report_scope"] == "INITIAL_OFFLINE"
    assert body["balances"]["credited_zat"] == 0 and body["balances"]["candidate_zat"] == 100_000
    assert (
        body["balances"]["outstanding_zat"] == 200_000
        and body["balances"]["projected_outstanding_zat"] == 100_000
    )
    assert body["balances"]["eligible_for_credit"] is False
    detail = api.get(f"/api/cases/{case}", headers=headers)
    assert detail.status_code == 200 and detail.json()["version"] == 3


def test_verification_and_report_require_ownership_and_reject_chain_spoofing(
    database, verification_api
):
    api, headers, case, evidence = verification_api
    path = f"/api/cases/{case}/verify"
    assert api.post(path, json={"evidence_id": evidence}).status_code == 401
    assert api.get(f"/api/cases/{case}/report").status_code == 401
    for extra in ({"chain_state": "CONFIRMED"}, {"confirmed": True}, {"amount_zat": 100_000}):
        assert (
            api.post(path, headers=headers, json={"evidence_id": evidence, **extra}).status_code
            == 422
        )
    with Session(database) as session, session.begin():
        other = provision_merchant(session, "Other")
    foreign = {"Authorization": "Bearer " + other.token, "Idempotency-Key": "test"}
    assert api.post(path, headers=foreign, json={"evidence_id": evidence}).status_code == 404
    assert api.get(f"/api/cases/{case}/report", headers=foreign).status_code == 404
    assert (
        api.get(
            f"/api/cases/{case}/report",
            headers=headers,
            params={"verification_id": str(uuid.uuid4())},
        ).status_code
        == 404
    )


def test_workflow_capacity_matches_existing_verifier_limit(verification_api):
    api, headers, case, evidence = verification_api
    slots = api.app.state.verifier_slots
    assert slots.acquire(blocking=False) and slots.acquire(blocking=False)
    try:
        assert (
            api.post(
                f"/api/cases/{case}/verify", headers=headers, json={"evidence_id": evidence}
            ).status_code
            == 429
        )
    finally:
        slots.release()
        slots.release()
