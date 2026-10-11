import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_persisted_verification import verification_setup as verification_setup
from zecsolve.auth.credentials import provision_merchant
from zecsolve.config import Settings
from zecsolve.main import create_app

pytestmark = pytest.mark.postgres
ORIGIN = "https://app.example"
SESSION = "__Host-zecsolve_session"
CSRF = "__Host-zecsolve_csrf"


@pytest.fixture
def session_api(database, root, monkeypatch):
    monkeypatch.setattr("zecsolve.main.make_engine", lambda settings: database)
    app = create_app(
        Settings(
            _env_file=None,
            browser_origins=[ORIGIN],
            verifier_path=root / "target/debug/zecsolve-verifier",
            migrations_path=root / "apps/api/migrations",
        )
    )
    with Session(database) as session, session.begin():
        issued = provision_merchant(session, "Browser merchant")
    with TestClient(app, base_url=ORIGIN) as api:
        yield api, issued, app


def login(api, code):
    return api.post("/api/session", json={"code": code}, headers={"Origin": ORIGIN})


def test_session_http_sets_secure_cookies_and_requires_csrf_for_cookie_writes(session_api):
    api, issued, _ = session_api
    response = login(api, issued.token)
    assert response.status_code == 201
    cookies = response.headers.get_list("set-cookie")
    assert any(
        SESSION in value
        and "HttpOnly" in value
        and "Secure" in value
        and "SameSite=strict" in value
        and "Path=/" in value
        for value in cookies
    )
    assert (
        api.cookies.get(SESSION) not in response.text and api.cookies.get(CSRF) not in response.text
    )
    assert api.get("/api/session").json()["access"]["role"] == "merchant"
    assert api.get("/api/auth/me").json()["merchant_id"] == str(issued.merchant_id)
    for headers in (
        {},
        {"Origin": "https://evil.example", "X-CSRF-Token": api.cookies.get(CSRF)},
        {"Origin": ORIGIN, "X-CSRF-Token": "bad"},
    ):
        assert api.post("/api/cases", json={}, headers=headers).status_code == 403
    headers = {"Origin": ORIGIN, "X-CSRF-Token": api.cookies.get(CSRF)}
    assert api.post("/api/cases", json={}, headers=headers).status_code == 422
    assert api.delete("/api/session", headers=headers).status_code == 204
    assert api.cookies.get(SESSION) is None and api.cookies.get(CSRF) is None
    assert api.get("/api/session").status_code == 401


def test_login_rejects_untrusted_origins_and_preserves_bearer_auth(session_api):
    api, issued, app = session_api
    for origin in (None, "null", "https://app.example.evil.test"):
        headers = {"Origin": origin} if origin else {}
        assert (
            api.post("/api/session", json={"code": issued.token}, headers=headers).status_code
            == 403
        )
    assert (
        api.post(
            "/api/session", json={"code": "zsm_" + "x" * 43}, headers={"Origin": ORIGIN}
        ).status_code
        == 401
    )
    assert (
        api.get("/api/auth/me", headers={"Authorization": "Bearer " + issued.token}).status_code
        == 200
    )
    app.state.browser_origins = frozenset()
    assert login(api, issued.token).status_code == 503


def test_grant_sessions_cannot_enter_merchant_routes(database, session_api, verification_setup):
    from zecsolve.schemas.grant import GrantCreateRequest
    from zecsolve.services.grants import GrantService

    api, _, _ = session_api
    _, principal, case, _, _ = verification_setup
    for scope in ({"role": "customer"}, {"role": "reviewer", "report_sections": ["case"]}):
        created, _ = GrantService(database).create(
            principal, case.case_id, GrantCreateRequest(scope=scope), scope["role"]
        )
        assert login(api, created.access_code).status_code == 201
        assert api.get("/api/session").json()["access"]["role"] == scope["role"]
        headers = {"Origin": ORIGIN, "X-CSRF-Token": api.cookies.get(CSRF)}
        for method, path, body in [
            ("get", "/api/cases", None),
            ("get", f"/api/cases/{case.case_id}/report", None),
            ("post", f"/api/cases/{case.case_id}/verify", {}),
            ("post", f"/api/cases/{case.case_id}/resolve", {}),
            ("post", f"/api/cases/{case.case_id}/grants", {}),
        ]:
            assert api.request(method, path, headers=headers, json=body).status_code == 403
        GrantService(database).revoke(principal, case.case_id, created.grant.grant_id)
        assert api.get("/api/session").status_code == 401
