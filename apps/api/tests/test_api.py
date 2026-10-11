from fastapi.testclient import TestClient
from zecsolve.config import Settings
from zecsolve.main import create_app


def client(root, token="test-poc-token"):
    return TestClient(
        create_app(
            Settings(
                _env_file=None,
                poc_token=token,
                verifier_path=root / "target/debug/zecsolve-verifier",
                database_url="postgresql+psycopg://absent@127.0.0.1:1/absent",
            )
        )
    )


def test_health_is_honest_when_database_unavailable(root):
    with client(root) as api:
        assert api.get("/health/live").json()["name"] == "zecsolve"
        response = api.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {
            "database_migrated": False,
            "verifier_available": True,
            "evidence_encryption_configured": False,
        }


def test_poc_requires_token_and_returns_real_recovery(root, receipt, raw_tx):
    with client(root) as api:
        payload = {"receipt_json": receipt, "raw_tx_hex": raw_tx}
        assert api.post("/api/poc/verify", json=payload).status_code == 401
        response = api.post(
            "/api/poc/verify", json=payload, headers={"Authorization": "Bearer test-poc-token"}
        )
        assert response.status_code == 200
        assert response.json()["output"]["amount_zat"] == 100_000
        assert response.json()["chain_state"] == "UNAVAILABLE"
        assert response.headers["cache-control"] == "no-store"


def test_poc_disabled_without_configured_token(root):
    with client(root, token="") as api:
        assert api.post("/api/poc/verify", json={}).status_code == 503


def test_validation_does_not_echo_disclosure(root):
    with client(root) as api:
        response = api.post(
            "/api/poc/verify",
            json={"receipt_json": {"ock": "secret-disclosure"}},
            headers={"Authorization": "Bearer test-poc-token"},
        )
        assert response.status_code == 422
        assert "secret-disclosure" not in response.text


def test_request_body_limit(root):
    with client(root) as api:
        response = api.post("/api/poc/verify", content=b"x" * 4_200_001)
        assert response.status_code == 413


def test_unpaired_unicode_is_rejected_without_echoing_input(root):
    with client(root) as api:
        response = api.post(
            "/api/poc/verify",
            content=b'{"receipt_json": "\\ud800"}',
            headers={
                "Authorization": "Bearer test-poc-token",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 422
        assert "ud800" not in response.text
