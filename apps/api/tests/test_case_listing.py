import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select, text, update
from sqlalchemy.orm import Session
from zecsolve.auth.credentials import (
    MerchantPrincipal,
    issue_credential,
    provision_merchant,
    revoke_credential,
)
from zecsolve.config import Settings
from zecsolve.db.models import Case, Invoice, MerchantCredential
from zecsolve.domain.statuses import CaseState
from zecsolve.main import create_app
from zecsolve.schemas.case import CaseListQuery
from zecsolve.services.case_cursor import encode_case_cursor
from zecsolve.services.cases import CaseService
from zecsolve.services.workflow import WorkflowError

pytestmark = pytest.mark.postgres
SUMMARY_FIELDS = {
    "schema_version",
    "case_id",
    "invoice_id",
    "merchant_id",
    "state",
    "version",
    "created_at",
}


@pytest.fixture
def listing_api(database, root, monkeypatch):
    monkeypatch.setattr("zecsolve.main.make_engine", lambda settings: database)
    app = create_app(
        Settings(_env_file=None, verifier_path=root / "target/debug/zecsolve-verifier")
    )
    with Session(database) as session, session.begin():
        merchant = provision_merchant(session, "Listing merchant")
        other = provision_merchant(session, "Other merchant")
    with TestClient(app) as api:
        yield api, merchant, other


def headers(merchant):
    return {"Authorization": "Bearer " + merchant.token}


def seed_cases(database, merchant, count, *, start=1, state=None, at=None):
    """Synthetic legacy metadata exercises listing only, never payment verification."""
    cases = []
    with Session(database) as session, session.begin():
        for i in range(start, start + count):
            invoice = Invoice(
                id=uuid.uuid4(),
                merchant_id=merchant.merchant_id,
                network="mainnet",
                pool="orchard",
                expected_zat=1,
                expected_receiver="private-receiver",
                receiver_hex="00" * 43,
                expected_memo=b"private-memo",
                snapshot_hash="ab" * 32,
                policy_version="legacy",
            )
            session.add(invoice)
            session.flush()
            case = Case(
                id=uuid.UUID(int=i),
                invoice_id=invoice.id,
                merchant_id=merchant.merchant_id,
                state=state or list(CaseState)[i % len(CaseState)].value,
                version=i,
                category="private-category",
                created_at=at or datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=i % 5),
            )
            session.add(case)
            cases.append((case.created_at, case.id))
    return [str(case_id) for _, case_id in sorted(cases, reverse=True)]


def test_empty_listing_and_input_validation(listing_api):
    api, merchant, _ = listing_api
    response = api.get("/api/cases", headers=headers(merchant))
    assert response.status_code == 200
    assert response.json() == {"schema_version": "1", "items": [], "next_cursor": None}
    assert response.headers["cache-control"] == "no-store"
    for params in (
        {"limit": 0},
        {"limit": 101},
        {"limit": "bad"},
        {"state": "PAID"},
        {"cursor": ""},
        {"cursor": "a" * 513},
        {"cursor": "private+cursor"},
        {"merchant_id": "private-merchant"},
        {"offset": 1},
    ):
        response = api.get("/api/cases", headers=headers(merchant), params=params)
        assert response.status_code == 422
        assert "private" not in response.text
        assert response.headers["cache-control"] == "no-store"


def test_bounded_pages_are_stable_and_merchant_owned(database, listing_api):
    api, merchant, other = listing_api
    expected = seed_cases(database, merchant, 103)
    seed_cases(database, other, 10, start=1000)
    first = api.get("/api/cases", headers=headers(merchant)).json()
    assert len(first["items"]) == 50 and first["next_cursor"]
    maximum = api.get("/api/cases", headers=headers(merchant), params={"limit": 100}).json()
    assert len(maximum["items"]) == 100 and maximum["next_cursor"]
    seen = []
    params = {"limit": 7}
    for _ in range(16):
        response = api.get("/api/cases", headers=headers(merchant), params=params)
        assert response.status_code == 200
        page = response.json()
        assert len(page["items"]) <= 7
        for item in page["items"]:
            assert set(item) == SUMMARY_FIELDS
            assert item["merchant_id"] == str(merchant.merchant_id)
            assert item["created_at"].endswith("Z")
            assert item["version"] == uuid.UUID(item["case_id"]).int
        assert "private" not in response.text and merchant.token not in response.text
        seen.extend(item["case_id"] for item in page["items"])
        if page["next_cursor"] is None:
            break
        params["cursor"] = page["next_cursor"]
    else:
        pytest.fail("Pagination did not terminate")
    assert seen == expected
    assert len(set(seen)) == 103
    # Summary metadata may include historical cases; detail must still refuse invented history.
    detail = api.get("/api/cases/" + seen[0], headers=headers(merchant))
    assert detail.status_code == 409
    assert detail.json()["detail"] == "LEGACY_CASE_HISTORY_UNAVAILABLE"


@pytest.mark.parametrize("state", list(CaseState))
def test_state_filter_applies_to_every_page(database, listing_api, state):
    api, merchant, other = listing_api
    all_ids = seed_cases(database, merchant, 15)
    seed_cases(database, other, 1, start=1000, state=state.value)
    expected = [i for i in all_ids if list(CaseState)[uuid.UUID(i).int % len(CaseState)] == state]
    response = api.get(
        "/api/cases", headers=headers(merchant), params={"state": state.value, "limit": 2}
    )
    assert response.status_code == 200
    first = response.json()
    second = api.get(
        "/api/cases",
        headers=headers(merchant),
        params={
            "state": state.value,
            "limit": 2,
            "cursor": first["next_cursor"],
        },
    ).json()
    items = first["items"] + second["items"]
    assert [item["case_id"] for item in items] == expected
    assert all(item["state"] == state.value for item in items)
    assert second["next_cursor"] is None


def test_pages_survive_anchor_state_change_and_newer_insert(database, listing_api):
    api, merchant, _ = listing_api
    expected = seed_cases(database, merchant, 3, state="OPEN")
    first = api.get("/api/cases", headers=headers(merchant), params={"state": "OPEN", "limit": 1})
    cursor = first.json()["next_cursor"]
    with database.begin() as connection:
        connection.execute(
            update(Case)
            .where(Case.id == uuid.UUID(expected[0]))
            .values(
                state="UNDER_REVIEW",
                version=Case.version + 1,
            )
        )
    seed_cases(database, merchant, 1, start=100, state="OPEN", at=datetime(2026, 2, 1, tzinfo=UTC))
    page = api.get(
        "/api/cases",
        headers=headers(merchant),
        params={
            "state": "OPEN",
            "cursor": cursor,
            "limit": 10,
        },
    ).json()
    assert [item["case_id"] for item in page["items"]] == expected[1:]
    assert page["next_cursor"] is None
    assert (
        api.get(
            "/api/cases",
            headers=headers(merchant),
            params={
                "state": "RESOLVED",
            },
        ).json()["items"]
        == []
    )


def test_cursor_cannot_cross_merchant_or_filter_even_when_forged(database, listing_api):
    api, merchant, other = listing_api
    seed_cases(database, merchant, 2, state="OPEN")
    foreign = seed_cases(database, other, 2, start=1000, state="OPEN")
    other_page = api.get("/api/cases", headers=headers(other), params={"limit": 1}).json()
    tokens = [
        other_page["next_cursor"],
        encode_case_cursor(merchant.merchant_id, uuid.UUID(foreign[0]), None),
        encode_case_cursor(merchant.merchant_id, uuid.uuid4(), None),
        encode_case_cursor(merchant.merchant_id, uuid.UUID(int=2), CaseState.OPEN),
        "not_json",
    ]
    for token in tokens:
        response = api.get("/api/cases", headers=headers(merchant), params={"cursor": token})
        assert response.status_code == 422
        assert response.json() == {"detail": "INVALID_CASE_CURSOR"}
        assert other.token not in response.text and foreign[0] not in response.text
    # Rotation within the same merchant preserves pagination; cursors carry no credentials.
    with Session(database) as session, session.begin():
        replacement = issue_credential(session, other.merchant_id)
    continuation = api.get(
        "/api/cases",
        headers=headers(replacement),
        params={
            "cursor": other_page["next_cursor"],
        },
    ).json()
    assert [item["case_id"] for item in continuation["items"]] == foreign[1:]


@pytest.mark.parametrize("invalidity", ["revoked", "expired"])
def test_listing_requires_current_credentials_in_api_and_service(database, listing_api, invalidity):
    api, merchant, _ = listing_api
    seed_cases(database, merchant, 1)
    assert api.get("/api/cases").status_code == 401
    assert api.get("/api/cases", headers={"Authorization": "Bearer invalid"}).status_code == 401
    with Session(database) as session, session.begin():
        if invalidity == "revoked":
            revoke_credential(session, merchant.credential_id)
        else:
            now = session.scalar(select(func.clock_timestamp()))
            session.execute(
                update(MerchantCredential)
                .where(
                    MerchantCredential.id == merchant.credential_id,
                )
                .values(created_at=now - timedelta(days=2), expires_at=now - timedelta(days=1))
            )
    assert api.get("/api/cases", headers=headers(merchant)).status_code == 401
    with pytest.raises(WorkflowError, match="INVALID_MERCHANT_CREDENTIALS"):
        CaseService(database).list(
            MerchantPrincipal(merchant.merchant_id, merchant.credential_id), CaseListQuery()
        )


def test_listing_rechecks_expiry_after_reading_rows(database, listing_api):
    api, merchant, _ = listing_api
    seed_cases(database, merchant, 1)
    with database.begin() as connection:
        connection.execute(
            update(MerchantCredential)
            .where(
                MerchantCredential.id == merchant.credential_id,
            )
            .values(expires_at=func.clock_timestamp() + text("interval '2 seconds'"))
        )
    delayed = []

    def delay_after_read(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("SELECT cases.id AS case_id"):
            delayed.append(True)
            connection.exec_driver_sql("SELECT pg_sleep(2.1)")

    event.listen(database, "after_cursor_execute", delay_after_read)
    try:
        response = api.get("/api/cases", headers=headers(merchant))
    finally:
        event.remove(database, "after_cursor_execute", delay_after_read)
    assert delayed == [True]
    assert response.status_code == 401
    assert "items" not in response.json()


def test_new_case_appears_without_changing_detail_contract(database, listing_api, root):
    api, merchant, _ = listing_api
    manifest = json.loads((root / "fixtures/manifest.json").read_text())
    auth = {**headers(merchant), "Idempotency-Key": "listing-new-case"}
    invoice = api.post(
        "/api/invoices",
        headers=auth,
        json={
            "expected_zat": 200_000,
            "network": "mainnet",
            "pool": "orchard",
            "receiver_address": manifest["expected"]["receiver_address"],
        },
    )
    assert invoice.status_code == 201
    opened = api.post("/api/cases", headers=auth, json={"invoice_id": invoice.json()["invoice_id"]})
    assert opened.status_code == 201
    listing = api.get("/api/cases", headers=headers(merchant)).json()
    assert listing["items"] == [{k: v for k, v in opened.json().items() if k in SUMMARY_FIELDS}]
    assert api.get(opened.headers["location"], headers=auth).json() == opened.json()


def test_database_failure_returns_no_internal_details(database, listing_api):
    api, merchant, _ = listing_api
    with database.begin() as connection:
        connection.execute(text("ALTER TABLE cases RENAME TO unavailable_cases"))
    response = api.get("/api/cases", headers=headers(merchant))
    assert response.status_code == 503
    assert response.json() == {"detail": "CASE_SERVICE_UNAVAILABLE"}
    assert response.headers["cache-control"] == "no-store"
