import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from zecsolve.auth.credentials import provision_merchant, revoke_credential
from zecsolve.config import Settings
from zecsolve.db.models import Case, CaseCreationRequest, CaseEvent
from zecsolve.main import create_app

pytestmark = pytest.mark.postgres


@pytest.fixture
def case_api(database, root, monkeypatch):
    monkeypatch.setattr("zecsolve.main.make_engine", lambda settings: database)
    app = create_app(
        Settings(
            _env_file=None,
            verifier_path=root / "target/debug/zecsolve-verifier",
            migrations_path=root / "apps/api/migrations",
        )
    )
    with Session(database) as session, session.begin():
        merchant = provision_merchant(session, "Case API")
    headers = {"Authorization": "Bearer " + merchant.token, "Idempotency-Key": "shared-key"}
    with TestClient(app) as api:
        manifest = json.loads((root / "fixtures/manifest.json").read_text())
        response = api.post(
            "/api/invoices",
            headers=headers,
            json={
                "expected_zat": 200_000,
                "network": "mainnet",
                "pool": "orchard",
                "receiver_address": manifest["expected"]["receiver_address"],
            },
        )
        assert response.status_code == 201
        yield api, headers, response.json()["invoice_id"], merchant


def test_create_read_and_idempotent_case_opening(database, case_api):
    api, headers, invoice, merchant = case_api
    response = api.post("/api/cases", headers=headers, json={"invoice_id": invoice})
    assert response.status_code == 201
    opened = response.json()
    assert opened["state"] == "OPEN" and opened["version"] == 1
    assert opened["merchant_id"] == str(merchant.merchant_id)
    assert opened["opening_event"]["action"] == "CASE_OPENED"
    assert response.headers["cache-control"] == "no-store"
    assert merchant.token not in response.text
    assert api.get(response.headers["location"], headers=headers).json() == opened
    for key in [headers["Idempotency-Key"], "another-key"]:
        replay = api.post(
            "/api/cases", headers={**headers, "Idempotency-Key": key}, json={"invoice_id": invoice}
        )
        assert replay.status_code == 200 and replay.json() == opened
        assert replay.headers["idempotency-replayed"] == "true"
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(Case)) == 1
        assert session.scalar(select(func.count()).select_from(CaseEvent)) == 1


def test_case_routes_enforce_merchant_access_and_revocation(database, case_api):
    api, headers, invoice, merchant = case_api
    assert api.post("/api/cases", json={"invoice_id": invoice}).status_code == 401
    response = api.post("/api/cases", headers=headers, json={"invoice_id": invoice})
    assert response.status_code == 201
    with Session(database) as session, session.begin():
        other = provision_merchant(session, "Other")
    foreign = {"Authorization": "Bearer " + other.token, "Idempotency-Key": "other"}
    assert api.post("/api/cases", headers=foreign, json={"invoice_id": invoice}).status_code == 404
    assert api.get(response.headers["location"], headers=foreign).status_code == 404
    assert api.get("/api/cases/" + str(uuid.uuid4()), headers=foreign).status_code == 404
    with Session(database) as session, session.begin():
        revoke_credential(session, merchant.credential_id)
    assert api.get(response.headers["location"], headers=headers).status_code == 401
    assert api.post("/api/cases", headers=headers, json={"invoice_id": invoice}).status_code == 401


@pytest.mark.parametrize(
    "extra",
    [
        {"merchant_id": "forged"},
        {"actor": "forged"},
        {"state": "RESOLVED"},
        {"payload": {}},
        {"version": 2},
    ],
)
def test_case_rejects_caller_controlled_workflow_fields(database, case_api, extra):
    api, headers, invoice, _ = case_api
    response = api.post("/api/cases", headers=headers, json={"invoice_id": invoice, **extra})
    assert response.status_code == 422 and "forged" not in response.text
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(Case)) == 0


def test_case_requires_key_and_does_not_repurpose_it(case_api):
    api, headers, invoice, _ = case_api
    assert (
        api.post(
            "/api/cases",
            headers={"Authorization": headers["Authorization"]},
            json={"invoice_id": invoice},
        ).status_code
        == 422
    )
    assert api.post("/api/cases", headers=headers, json={"invoice_id": invoice}).status_code == 201
    assert (
        api.post("/api/cases", headers=headers, json={"invoice_id": str(uuid.uuid4())}).status_code
        == 409
    )


def test_case_database_errors_are_private_and_atomic(database, case_api):
    api, headers, invoice, _ = case_api
    with database.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION reject_opening() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'private-case-detail'; END; $$"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER reject_opening BEFORE INSERT ON case_events "
                "FOR EACH ROW EXECUTE FUNCTION reject_opening()"
            )
        )
    response = api.post("/api/cases", headers=headers, json={"invoice_id": invoice})
    assert response.status_code == 503 and "private-case-detail" not in response.text
    with Session(database) as session:
        for model in (Case, CaseEvent, CaseCreationRequest):
            assert session.scalar(select(func.count()).select_from(model)) == 0
