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
def evidence_api(database, root, receipt, raw_tx, monkeypatch):
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
        merchant = provision_merchant(session, "Evidence API")
    headers = {"Authorization": "Bearer " + merchant.token, "Idempotency-Key": "shared"}
    with TestClient(app) as api:
        address = json.loads((root / "fixtures/manifest.json").read_text())["expected"][
            "receiver_address"
        ]
        invoice = api.post(
            "/api/invoices",
            headers=headers,
            json={
                "expected_zat": 200_000,
                "network": "mainnet",
                "pool": "orchard",
                "receiver_address": address,
            },
        ).json()
        case = api.post(
            "/api/cases", headers=headers, json={"invoice_id": invoice["invoice_id"]}
        ).json()
        request = {
            "receipt_json": receipt,
            "raw_tx_hex": raw_tx,
            "source": "public fixture",
            "source_kind": "public_fixture",
            "processing_authorized": True,
        }
        yield api, headers, case["case_id"], request


def test_evidence_endpoint_returns_metadata_and_replays_without_disclosure(evidence_api):
    api, headers, case, body = evidence_api
    path = f"/api/cases/{case}/evidence"
    response = api.post(path, headers=headers, json=body)
    assert response.status_code == 201
    result = response.json()
    assert result["case_version"] == 2 and result["receipt_sha256"]
    assert (
        "receipt_json" not in result and "raw_tx_hex" not in result and "ciphertext" not in result
    )
    assert body["receipt_json"] not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert api.get(response.headers["location"], headers=headers).json() == result
    replay = api.post(path, headers=headers, json=body)
    assert replay.status_code == 200 and replay.json() == result
    assert api.get(f"/api/cases/{case}", headers=headers).json()["version"] == 2


def test_evidence_routes_reject_foreign_access_and_unacknowledged_input(database, evidence_api):
    api, headers, case, body = evidence_api
    path = f"/api/cases/{case}/evidence"
    assert api.post(path, json=body).status_code == 401
    for change in [
        {"processing_authorized": False},
        {"share_with_reviewers": True},
        {"merchant_id": "forged"},
        {"source": "bad\0label"},
    ]:
        response = api.post(path, headers=headers, json={**body, **change})
        assert response.status_code == 422 and "ock" not in response.text
    created = api.post(path, headers=headers, json=body)
    assert created.status_code == 201
    with Session(database) as session, session.begin():
        other = provision_merchant(session, "Other")
    foreign = {"Authorization": "Bearer " + other.token, "Idempotency-Key": "other"}
    assert api.post(path, headers=foreign, json=body).status_code == 404
    assert api.get(created.headers["location"], headers=foreign).status_code == 404
    assert (
        api.get(
            f"/api/cases/{uuid.uuid4()}/evidence/{created.json()['evidence_id']}", headers=headers
        ).status_code
        == 404
    )


def test_encryption_configuration_controls_readiness_and_new_uploads(evidence_api):
    from pydantic import SecretStr
    from zecsolve.adapters.evidence_crypto import EvidenceCipher

    api, headers, case, body = evidence_api
    assert api.get("/health/ready").status_code == 200
    api.app.state.evidence_cipher = EvidenceCipher("", SecretStr(""))
    ready = api.get("/health/ready")
    assert ready.status_code == 503 and ready.json()["evidence_encryption_configured"] is False
    response = api.post(f"/api/cases/{case}/evidence", headers=headers, json=body)
    assert response.status_code == 503


def test_evidence_submission_uses_shared_capacity(evidence_api):
    api, headers, case, body = evidence_api
    slots = api.app.state.verifier_slots
    assert slots.acquire(blocking=False) and slots.acquire(blocking=False)
    try:
        assert (
            api.post(f"/api/cases/{case}/evidence", headers=headers, json=body).status_code == 429
        )
    finally:
        slots.release()
        slots.release()
