import json
import os
import subprocess
import sys

import certifi
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from zecsolve.config import Settings
from zecsolve.deployment import vercel


@pytest.fixture
def vercel_environment(monkeypatch):
    for key, value in {
        "VERCEL": "1",
        "VERCEL_ENV": "preview",
        "PORT": "8123",
        "ZECSOLVE_DEPLOY_HOST": "zecsolve.example.test",
        "ZECSOLVE_DATABASE_URL": (
            "postgresql+psycopg://user:private-password@db.example.test/db?sslmode=verify-full"
        ),
        "ZECSOLVE_BROWSER_ORIGINS": '["https://zecsolve.example.test"]',
        "ZECSOLVE_EVIDENCE_KEY_ID": "test-key",
        "ZECSOLVE_EVIDENCE_KEY": "private-test-key",
        "ZECSOLVE_RPC_URL": "https://rpc.example.test",
        "ZECSOLVE_RPC_ALLOW_PRIVATE_HTTP": "false",
    }.items():
        monkeypatch.setenv(key, value)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("VERCEL", ""),
        ("VERCEL_ENV", "development"),
        ("PORT", "0"),
        ("PORT", "65536"),
        ("ZECSOLVE_DATABASE_URL", "postgresql+psycopg://db.example.test/db?sslmode=require"),
        ("ZECSOLVE_BROWSER_ORIGINS", "[]"),
        ("ZECSOLVE_BROWSER_ORIGINS", '["https://other.example.test"]'),
        ("ZECSOLVE_EVIDENCE_KEY", ""),
        ("ZECSOLVE_EVIDENCE_KEY_ID", ""),
        ("ZECSOLVE_RPC_URL", ""),
        ("ZECSOLVE_RPC_ALLOW_PRIVATE_HTTP", "true"),
    ],
)
def test_incomplete_or_unsafe_runtime_configuration_fails(
    vercel_environment, monkeypatch, key, value
):
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        vercel.runtime_configuration()


def test_server_uses_platform_port_without_startup_migrations(vercel_environment, monkeypatch):
    events = []
    app = object()
    monkeypatch.setattr(vercel, "require_current_schema", lambda settings: events.append("schema"))
    monkeypatch.setattr(vercel, "create_app", lambda settings, deployment: app)
    monkeypatch.setattr(vercel.uvicorn, "run", lambda app, **kwargs: events.append((app, kwargs)))
    assert vercel.main() == 0
    assert events[0] == "schema"
    actual_app, options = events[1]
    assert actual_app is app
    assert options["port"] == 8123
    assert options["access_log"] is False
    assert options["limit_concurrency"] == 32


def test_database_uses_packaged_trust_roots_and_full_verification(vercel_environment):
    settings, _, _ = vercel.runtime_configuration()
    query = make_url(settings.database_url.get_secret_value()).query
    assert query["sslmode"] == "verify-full"
    assert query["sslrootcert"] == certifi.where()


def test_bad_startup_has_only_secret_safe_logs(vercel_environment):
    result = subprocess.run(
        [sys.executable, "-m", "zecsolve.deployment.vercel"],
        env={**os.environ, "PORT": "private-invalid-port"},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    events = [json.loads(line) for line in result.stderr.splitlines()]
    assert events and all(set(event) == {"level", "event"} for event in events)
    assert events[-1] == {"level": "ERROR", "event": "runtime_error"}


@pytest.mark.postgres
def test_runtime_checks_schema_without_modifying_it(database, monkeypatch):
    monkeypatch.setattr(vercel, "make_engine", lambda settings: database)
    settings = Settings(_env_file=None)
    vercel.require_current_schema(settings)
    with database.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num = '0008'"))
    with pytest.raises(ValueError, match="Apply release migrations"):
        vercel.require_current_schema(settings)
    with database.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0008"
