import json
import logging
import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from zecsolve.config import Settings
from zecsolve.deployment.app import create_app
from zecsolve.deployment.logging import SafeFormatter
from zecsolve.deployment.settings import DeploymentSettings, application_settings


@pytest.fixture
def deployed(tmp_path, root):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<!doctype html><title>Frontend build</title>")
    (web / "app.js").write_text("// built application")
    (tmp_path / "private.txt").write_text("PRIVATE-OUTSIDE-BUILD")
    (web / "leak.txt").symlink_to(tmp_path / "private.txt")
    (web / ".secret").write_text("PRIVATE-DOTFILE")
    deployment = DeploymentSettings(host="example.test", web_dist=web)
    settings = Settings(
        _env_file=None,
        poc_token="configured-but-disabled",
        database_url="postgresql+psycopg://absent@127.0.0.1:1/absent",
        verifier_path=root / "target/debug/zecsolve-verifier",
    )
    with TestClient(create_app(settings, deployment), base_url="https://example.test") as client:
        yield client


def test_built_app_and_browser_routes_share_origin(deployed):
    for path in ("/", "/cases", "/cases/example/report"):
        response = deployed.get(path, headers={"Accept": "text/html"})
        assert response.status_code == 200 and "Frontend build" in response.text
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["strict-transport-security"] == "max-age=31536000"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert deployed.get("/app.js").status_code == 200
    assert deployed.get("/api/cases").status_code == 401
    assert deployed.get("/health/live").json()["status"] == "ok"


@pytest.mark.parametrize(
    "path",
    [
        "/api/missing",
        "/health/missing",
        "/docs",
        "/docs/oauth2-redirect",
        "/redoc",
        "/openapi.json",
        "/missing.js",
        "/leak.txt",
        "/.secret",
        "/%2e%2e/private.txt",
    ],
)
def test_private_missing_and_reserved_paths_never_fall_back_to_html(deployed, path):
    response = deployed.get(path, headers={"Accept": "text/html"})
    assert response.status_code == 404
    assert "Frontend build" not in response.text and "PRIVATE" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_deployment_disables_poc_even_with_valid_token(deployed):
    response = deployed.post(
        "/api/poc/verify",
        json={},
        headers={
            "Authorization": "Bearer configured-but-disabled",
        },
    )
    assert response.status_code == 404


def test_untrusted_host_and_cleartext_requests_are_rejected(deployed):
    assert deployed.get("/", headers={"Host": "attacker.test"}).status_code == 400
    response = deployed.get("http://example.test/api/cases", headers={"X-Forwarded-Proto": "https"})
    assert response.status_code == 400
    assert "strict-transport-security" not in response.headers
    # Private container probes can use HTTP without redirect loops.
    assert deployed.get("http://example.test/health/live").status_code == 200


def test_readiness_preserves_dependency_failures(deployed):
    response = deployed.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {
        "database_migrated": False,
        "verifier_available": True,
        "evidence_encryption_configured": False,
    }


def test_existing_request_size_limit_is_preserved(deployed):
    response = deployed.post("/api/cases", content=b"x" * 4_200_001)
    assert response.status_code == 413
    assert response.headers["cache-control"] == "no-store"


def test_startup_requires_build_and_a_single_proxy_address(tmp_path):
    deployment = DeploymentSettings(host="localhost", web_dist=tmp_path)
    with pytest.raises(ValueError, match="Frontend build is missing"):
        create_app(Settings(_env_file=None), deployment)
    for fields in ({"host": "*"}, {"host": "bad/host"}, {"host": "localhost", "proxy_ip": "*"}):
        with pytest.raises(ValidationError):
            DeploymentSettings(**fields)


def test_application_secrets_are_loaded_from_mounted_files(tmp_path, monkeypatch):
    monkeypatch.delenv("ZECSOLVE_EVIDENCE_KEY", raising=False)
    (tmp_path / "ZECSOLVE_EVIDENCE_KEY").write_text("private-key-value")
    result = application_settings(DeploymentSettings(host="localhost", secrets_dir=tmp_path))
    assert result.evidence_key.get_secret_value() == "private-key-value"
    assert "private-key-value" not in repr(result)


def test_runtime_formatter_never_expands_messages_or_exceptions():
    try:
        raise ValueError("private-credential")
    except ValueError:
        record = logging.LogRecord(
            "private-path",
            logging.ERROR,
            "private-file",
            1,
            "Authorization: %s",
            ("private-token",),
            sys.exc_info(),
        )
    assert json.loads(SafeFormatter().format(record)) == {
        "level": "ERROR",
        "event": "runtime_error",
    }


def test_bad_startup_configuration_emits_only_safe_event():
    result = subprocess.run(
        [sys.executable, "-m", "zecsolve.deployment"],
        env={**os.environ, "ZECSOLVE_VERIFIER_TIMEOUT_SECONDS": "private-invalid-setting"},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 1
    assert "private-invalid-setting" not in result.stdout + result.stderr
    events = [json.loads(line) for line in result.stderr.splitlines()]
    assert events[-1] == {"level": "ERROR", "event": "runtime_error"}
    assert all(set(event) == {"level", "event"} for event in events)
