import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from zecsolve.auth.credentials import provision_merchant, revoke_credential
from zecsolve.config import Settings
from zecsolve.db.models import Invoice, InvoiceCreationRequest, InvoicePolicy
from zecsolve.main import create_app

pytestmark = pytest.mark.postgres


@pytest.fixture
def invoice_api(database, root, monkeypatch):
    monkeypatch.setattr("zecsolve.main.make_engine", lambda settings: database)
    app = create_app(
        Settings(
            _env_file=None,
            verifier_path=root / "target/debug/zecsolve-verifier",
            migrations_path=root / "apps/api/migrations",
            poc_token="test-poc-token",
        )
    )
    with TestClient(app) as client:
        yield client


@pytest.fixture
def invoice_body(root):
    address = json.loads((root / "fixtures/manifest.json").read_text())["expected"][
        "receiver_address"
    ]
    return {
        "expected_zat": 200_000,
        "network": "mainnet",
        "pool": "orchard",
        "receiver_address": address,
        "expected_memo": "glasspane first receipt",
    }


@pytest.fixture
def merchant(database):
    with Session(database) as session, session.begin():
        return provision_merchant(session, "Invoice API")


def headers(merchant, key="create-invoice"):
    return {"Authorization": "Bearer " + merchant.token, "Idempotency-Key": key}


def test_create_read_and_replay_invoice(invoice_api, invoice_body, merchant):
    response = invoice_api.post("/api/invoices", json=invoice_body, headers=headers(merchant))
    assert response.status_code == 201
    body = response.json()
    assert body["merchant_id"] == str(merchant.merchant_id)
    assert body["schema_version"] == "1"
    assert body["terms"]["expected_zat"] == 200_000
    assert body["policy"]["unique_receiver_binding"] is False
    assert body["terms"]["memo_hex"] == (b"glasspane first receipt" + bytes(489)).hex()
    assert response.headers["cache-control"] == "no-store"
    assert merchant.token not in response.text
    read = invoice_api.get(response.headers["location"], headers=headers(merchant))
    assert read.status_code == 200 and read.json() == body
    repeated = invoice_api.post("/api/invoices", json=invoice_body, headers=headers(merchant))
    assert repeated.status_code == 200 and repeated.json() == body
    assert repeated.headers["idempotency-replayed"] == "true"
    different = invoice_api.post(
        "/api/invoices", json={**invoice_body, "expected_zat": 1}, headers=headers(merchant)
    )
    assert different.status_code == 409


def test_authentication_and_merchant_isolation(database, invoice_api, invoice_body, merchant):
    assert invoice_api.post("/api/invoices", json=invoice_body).status_code == 401
    assert (
        invoice_api.post(
            "/api/invoices", json=invoice_body, headers={"Authorization": "Bearer test-poc-token"}
        ).status_code
        == 401
    )
    response = invoice_api.post("/api/invoices", json=invoice_body, headers=headers(merchant))
    assert response.status_code == 201
    with Session(database) as session, session.begin():
        other = provision_merchant(session, "Other")
    assert invoice_api.get(response.headers["location"], headers=headers(other)).status_code == 404
    assert (
        invoice_api.get("/api/invoices/" + str(uuid.uuid4()), headers=headers(other)).status_code
        == 404
    )
    with Session(database) as session, session.begin():
        revoke_credential(session, merchant.credential_id)
    assert (
        invoice_api.get(response.headers["location"], headers=headers(merchant)).status_code == 401
    )
    assert (
        invoice_api.post("/api/invoices", json=invoice_body, headers=headers(merchant)).status_code
        == 401
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"expected_zat": True},
        {"expected_zat": "200000"},
        {"merchant_id": "injected"},
        {"receiver_hex": "00" * 43},
        {"policy": {}},
        {"network": "testnet"},
        {"expected_memo": "é" * 257},
        {"expires_at": "2030-01-01T00:00:00"},
    ],
)
def test_invalid_input_has_no_side_effects(database, invoice_api, invoice_body, merchant, changes):
    response = invoice_api.post(
        "/api/invoices", json={**invoice_body, **changes}, headers=headers(merchant)
    )
    assert response.status_code == 422
    assert invoice_body["receiver_address"] not in response.text
    with Session(database) as session:
        for table in (Invoice, InvoicePolicy, InvoiceCreationRequest):
            assert session.scalar(select(func.count()).select_from(table)) == 0


def test_key_required_and_normalizer_capacity_shared_with_poc(invoice_api, invoice_body, merchant):
    assert (
        invoice_api.post(
            "/api/invoices",
            json=invoice_body,
            headers={"Authorization": "Bearer " + merchant.token},
        ).status_code
        == 422
    )
    slots = invoice_api.app.state.verifier_slots
    assert slots.acquire(blocking=False) and slots.acquire(blocking=False)
    try:
        assert (
            invoice_api.post(
                "/api/invoices", json=invoice_body, headers=headers(merchant)
            ).status_code
            == 429
        )
        assert (
            invoice_api.post(
                "/api/poc/verify", json={}, headers={"Authorization": "Bearer test-poc-token"}
            ).status_code
            == 429
        )
    finally:
        slots.release()
        slots.release()
    assert (
        invoice_api.post("/api/invoices", json=invoice_body, headers=headers(merchant)).status_code
        == 201
    )


def test_unavailable_normalizer_and_database_failure_are_generic(
    database, invoice_api, invoice_body, merchant, tmp_path
):
    binary = invoice_api.app.state.normalizer.binary
    invoice_api.app.state.normalizer.binary = tmp_path / "absent"
    assert (
        invoice_api.post("/api/invoices", json=invoice_body, headers=headers(merchant)).status_code
        == 503
    )
    invoice_api.app.state.normalizer.binary = binary
    with database.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION reject_invoice() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'private-db-detail'; END; $$"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER reject_invoice BEFORE INSERT ON invoices "
                "FOR EACH ROW EXECUTE FUNCTION reject_invoice()"
            )
        )
    response = invoice_api.post("/api/invoices", json=invoice_body, headers=headers(merchant))
    assert response.status_code == 503
    assert "private-db-detail" not in response.text and merchant.token not in response.text
