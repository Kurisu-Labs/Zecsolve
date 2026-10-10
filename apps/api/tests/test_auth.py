import argparse

import pytest
from fastapi.testclient import TestClient
from zecsolve.auth.cli import lifetime, main
from zecsolve.auth.credentials import token_digest
from zecsolve.config import Settings
from zecsolve.main import create_app


@pytest.mark.parametrize("token", ["", "test-poc-token", "zsm_short", "zsm_" + "x" * 44, "é" * 47])
def test_malformed_credentials_rejected_without_database_access(root, token):
    settings = Settings(
        _env_file=None,
        migrations_path=root / "apps/api/migrations",
        database_url="postgresql+psycopg://absent@127.0.0.1:1/absent",
    )
    with TestClient(create_app(settings)) as api:
        headers = {"Authorization": "Bearer " + token} if token and token.isascii() else {}
        response = api.get("/api/auth/me", headers=headers)
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {"detail": "Invalid merchant credentials"}
    assert token_digest(token) is None


def test_auth_database_failure_is_generic(root):
    token = "zsm_" + "a" * 43
    settings = Settings(
        _env_file=None,
        migrations_path=root / "apps/api/migrations",
        database_url="postgresql+psycopg://secret-user:secret-password@127.0.0.1:1/absent",
    )
    with TestClient(create_app(settings)) as api:
        response = api.get("/api/auth/me", headers={"Authorization": "Bearer " + token})
        assert response.status_code == 503
        assert response.json() == {"detail": "Merchant authentication unavailable"}
        assert "secret" not in response.text and token not in response.text


@pytest.mark.parametrize("value", ["0", "366", "-1", "1.5", "abc"])
def test_cli_rejects_bad_lifetime(value):
    with pytest.raises(argparse.ArgumentTypeError):
        lifetime(value)


def test_cli_argument_error_does_not_open_database(capsys):
    with pytest.raises(SystemExit) as error:
        main(["create-merchant", "--name", "Test", "--ttl-days", "0"])
    assert error.value.code == 2
    assert capsys.readouterr().out == ""
