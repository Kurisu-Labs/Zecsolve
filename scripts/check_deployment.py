"""Exercise the actual deployment in an isolated, disposable Compose project.

No live RPC, real customer data, public listener or existing database is used.
"""

import argparse
import base64
import http.client
import json
import os
import platform
import re
import secrets
import shutil
import socket
import ssl
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from http.cookies import SimpleCookie
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-on-failure", action="store_true")
    parser.add_argument(
        "--recovery", action="store_true", help="Also rehearse M7.2 backend recovery"
    )
    parser.add_argument(
        "--browser", action="store_true", help="Run P4's offline browser suite through nginx"
    )
    options = parser.parse_args()
    (ROOT / ".cache").mkdir(exist_ok=True)
    for name in ("deployment-result.json", "recovery-result.json"):
        (ROOT / ".cache" / name).unlink(missing_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="deployment-", dir=ROOT / ".cache"))
    project = "zecsolve-smoke-" + secrets.token_hex(4)
    http_port, https_port = free_port(), free_port()
    while https_port == http_port:
        https_port = free_port()
    subnet = f"172.30.{80 + secrets.randbelow(150)}"
    env = {
        **os.environ,
        "ZECSOLVE_DEPLOY_HOST": "localhost",
        "ZECSOLVE_DEPLOY_BIND": "127.0.0.1",
        "ZECSOLVE_DEPLOY_HTTP_PORT": str(http_port),
        "ZECSOLVE_DEPLOY_HTTPS_PORT": str(https_port),
        "ZECSOLVE_DEPLOY_SECRETS_DIR": str(directory),
        "ZECSOLVE_EVIDENCE_KEY_ID": "disposable-smoke-v1",
        "ZECSOLVE_BROWSER_ORIGINS": json.dumps([f"https://localhost:{https_port}"]),
        "ZECSOLVE_DEPLOY_SUBNET": subnet + ".0/24",
        "ZECSOLVE_DEPLOY_PROXY_IP": subnet + ".2",
        "ZECSOLVE_DEPLOY_API_IP": subnet + ".3",
        "ZECSOLVE_RPC_ALLOW_PRIVATE_HTTP": "false",
    }
    compose = ["docker-compose"] if shutil.which("docker-compose") else ["docker", "compose"]
    compose += ["-p", project, "-f", str(ROOT / "infra/compose.deployment.yaml")]
    # This contains deployment coordinates only, never generated credentials.
    (directory / "coordinates.json").write_text(
        json.dumps(
            {
                "project": project,
                "env": {
                    key: value for key, value in env.items() if key.startswith("ZECSOLVE_DEPLOY_")
                },
            }
        )
    )

    def run(args, *, check=True, input=None, binary=False):
        result = subprocess.run(
            args,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=not binary,
            input=input,
            check=False,
            timeout=1200,
        )
        if check and result.returncode:
            output = result.stdout + result.stderr
            (directory / "command-failure.log").write_text(
                output.decode(errors="replace") if binary else output
            )
            raise RuntimeError("Container command failed; private diagnostic retained on request")
        return result.stdout

    password = secrets.token_urlsafe(24)
    key = base64.b64encode(secrets.token_bytes(32)).decode()
    for name, value in {
        "database_password": password,
        "database_url": f"postgresql+psycopg://zecsolve:{password}@db:5432/zecsolve",
        "evidence_key": key,
        "rpc_url": "",
        "rpc_username": "",
        "rpc_password": "",
    }.items():
        (directory / name).write_text(value)
    run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "2",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost,IP:127.0.0.1",
            "-keyout",
            str(directory / "tls_key"),
            "-out",
            str(directory / "tls_certificate"),
        ]
    )
    for path in directory.iterdir():
        path.chmod(0o644)  # Non-root container users; host parent is private (0700).
    context = ssl.create_default_context(cafile=str(directory / "tls_certificate"))

    def request(path, *, method="GET", body=None, headers=None, chunked=False):
        connection = http.client.HTTPSConnection(
            "localhost", https_port, context=context, timeout=15
        )
        try:
            connection.request(
                method, path, body=body, headers=headers or {}, encode_chunked=chunked
            )
            response = connection.getresponse()
            return response.status, response.headers, response.read()
        finally:
            connection.close()

    results = []

    def passed(name):
        results.append(name)
        print("PASS: " + name, flush=True)

    success = False
    try:
        print("Building deployment image and starting disposable services...", flush=True)
        run(compose + ["up", "--build", "-d", "--wait", "--wait-timeout", "180"])
        status, headers, body = request("/health/ready")
        assert status == 200 and all(json.loads(body).values())
        assert headers["Strict-Transport-Security"] == "max-age=31536000"
        passed("trusted TLS certificate and migrated/encrypted/verifier readiness")
        connection = http.client.HTTPConnection("localhost", http_port, timeout=5)
        connection.request("GET", "/cases", headers={"Host": "attacker.test"})
        response = connection.getresponse()
        assert response.status == 308
        assert response.getheader("Location") == f"https://localhost:{https_port}/cases"
        connection.close()
        passed("HTTP redirects to the configured HTTPS hostname")
        status, _, html = request("/cases", headers={"Accept": "text/html"})
        assert status == 200 and b'<div id="app">' in html
        assets = re.findall(rb'(?:src|href)="(/assets/[^" ]+)"', html)
        assert assets and all(request(asset.decode())[0] == 200 for asset in assets)
        assert request("/api/cases")[0] == 401
        assert request("/api/missing", headers={"Accept": "text/html"})[0] == 404
        assert request("/assets/missing.js", headers={"Accept": "text/html"})[0] == 404
        assert request("/", headers={"Host": "attacker.test"})[0] == 400
        passed("actual frontend build, assets, SPA routes and API share one origin")
        assert request("/api/poc/verify", method="POST", body=b"{}")[0] == 404
        assert request("/openapi.json")[0] == 404
        passed("public POC and documentation routes are disabled")

        # Use P1's operator/service contracts with mounted settings; no alternate identity model.
        operator = """
import json, sys, uuid
from sqlalchemy.orm import Session
from zecsolve.auth.credentials import provision_merchant, revoke_credential
from zecsolve.db.session import make_engine
from zecsolve.deployment.settings import DeploymentSettings, application_settings
engine = make_engine(application_settings(DeploymentSettings()))
with Session(engine) as session, session.begin():
    if len(sys.argv) == 1:
        issued = provision_merchant(session, 'Disposable deployment merchant')
        result = {'token': issued.token, 'credential_id': str(issued.credential_id)}
    else:
        revoke_credential(session, uuid.UUID(sys.argv[1]))
        result = {'revoked': True}
engine.dispose()
print(json.dumps(result))
"""
        operator_command = compose + ["exec", "-T", "api", "python", "-c", operator]
        issued = json.loads(run(operator_command))
        origin = f"https://localhost:{https_port}"
        login_body = json.dumps({"code": issued["token"]})

        def session_request(path="/api/session", *, headers=None, **kwargs):
            time.sleep(0.25)  # Stay below the separately tested ingress rate limit.
            return request(
                path, headers={"Content-Type": "application/json", **(headers or {})}, **kwargs
            )

        time.sleep(3)
        for headers in ({}, {"Origin": "https://attacker.test"}):
            assert session_request(method="POST", body=login_body, headers=headers)[0] == 403

        session_secrets = [issued["token"]]

        def login():
            status, headers, body = session_request(
                method="POST", body=login_body, headers={"Origin": origin}
            )
            assert status == 201 and json.loads(body)["access"]["role"] == "merchant"
            cookies = SimpleCookie()
            for header in headers.get_all("Set-Cookie", []):
                cookies.load(header)
            assert set(cookies) == {"__Host-zecsolve_session", "__Host-zecsolve_csrf"}
            for cookie in cookies.values():
                assert cookie["secure"] and cookie["samesite"].lower() == "strict"
                assert cookie["path"] == "/" and not cookie["domain"]
                assert 0 < int(cookie["max-age"]) <= 8 * 60 * 60
                assert cookie.value.encode() not in body
                session_secrets.append(cookie.value)
            assert cookies["__Host-zecsolve_session"]["httponly"]
            assert not cookies["__Host-zecsolve_csrf"]["httponly"]
            return {
                "Cookie": "; ".join(f"{name}={cookie.value}" for name, cookie in cookies.items()),
                "Origin": origin,
                "X-CSRF-Token": cookies["__Host-zecsolve_csrf"].value,
            }

        session_headers = login()
        assert session_request(headers=session_headers)[0] == 200
        assert session_request("/api/cases", headers=session_headers)[0] == 200
        for overrides in (
            {"Origin": ""},
            {"Origin": "https://attacker.test"},
            {"X-CSRF-Token": "bad"},
        ):
            assert (
                session_request(method="DELETE", headers={**session_headers, **overrides})[0] == 403
            )
        assert session_request(headers=session_headers)[0] == 200
        status, cleared, _ = session_request(method="DELETE", headers=session_headers)
        assert status == 204
        assert len(cleared.get_all("Set-Cookie", [])) == 2
        assert all("Max-Age=0" in value for value in cleared.get_all("Set-Cookie"))
        assert session_request(headers=session_headers)[0] == 401
        session_headers = login()
        assert json.loads(run(operator_command + [issued["credential_id"]]))["revoked"]
        assert session_request(headers=session_headers)[0] == 401
        assert session_request(method="POST", body=login_body, headers={"Origin": origin})[0] == 401
        passed("TLS session cookies, restoration, Origin/CSRF, logout and parent revocation")

        time.sleep(3)  # Drain the ingress token bucket before testing independent limits.
        assert request("/api/cases", method="POST", body=b"x" * 4_200_001)[0] == 413
        assert (
            request("/api/cases", method="POST", body=iter([b"x" * 1_000_000] * 5), chunked=True)[0]
            == 413
        )
        passed("ingress rejects oversized fixed-length and chunked bodies")
        marker = "private-smoke-" + secrets.token_hex(8)

        def burst(_):
            return request(
                "/api/cases?access_code=" + marker,
                headers={
                    "Authorization": "Bearer " + marker,
                    "X-Forwarded-For": secrets.token_hex(4),
                },
            )[0]

        with ThreadPoolExecutor(max_workers=20) as executor:
            statuses = list(executor.map(burst, range(60)))
        assert 429 in statuses and set(statuses) <= {401, 429}
        passed("API rate limit cannot be bypassed with forwarded client headers")
        for service, memory, cpus in (
            ("api", 1073741824, 2000000000),
            ("ingress", 134217728, 500000000),
        ):
            container = run(compose + ["ps", "-q", service]).strip()
            inspected = json.loads(run(["docker", "inspect", container]))[0]
            host = inspected["HostConfig"]
            assert host["Memory"] == memory and host["NanoCpus"] == cpus
            assert host["ReadonlyRootfs"] and "ALL" in host["CapDrop"]
            assert host["PidsLimit"] > 0 and "no-new-privileges:true" in host["SecurityOpt"]
            assert inspected["Config"]["User"] not in {"", "0", "root"}
            if service == "api":
                assert not host["PortBindings"]
        passed("non-root containers enforce memory/CPU/PID limits and private API binding")
        database = run(compose + ["ps", "-q", "db"]).strip()
        database_host = json.loads(run(["docker", "inspect", database]))[0]["HostConfig"]
        assert database_host["LogConfig"]["Type"] == "none"
        run(compose + ["stop", "db"])
        assert request("/health/ready")[0] == 503 and request("/health/live")[0] == 200
        run(compose + ["start", "db"])
        for _ in range(30):
            if request("/health/ready")[0] == 200:
                break
            time.sleep(1)
        else:
            raise AssertionError("Readiness did not recover")
        passed("readiness fails during database outage and recovers after restart")
        logs = run(compose + ["logs", "--no-color", "api", "ingress"])
        assert all(secret not in logs for secret in [marker, password, key, *session_secrets])
        passed("container logs exclude request codes, authorization and configured secrets")
        recovery = None
        if options.recovery:
            from check_recovery import rehearse

            recovery = rehearse(ROOT, directory, compose, run, request, origin, passed)
        browser = None
        if options.browser:
            from browser_acceptance import run_suite

            # Separate merchant: recovery scenarios must not alter browser listing counts.
            browser_merchant = json.loads(run(operator_command))
            state = directory / "browser-state.json"
            state.write_text(
                json.dumps({"merchant_code": browser_merchant["token"], "simulated": False})
            )
            state.chmod(0o600)
            time.sleep(3)  # Drain prior recovery requests from the real ingress bucket.
            browser = run_suite(directory / "browser", state, origin, ingress=True)
            passed("eight real-browser scenarios through packaged frontend and nginx TLS ingress")
            logs = run(compose + ["logs", "--no-color", "api", "ingress"])
            assert browser_merchant["token"] not in logs
            passed("browser merchant access code is absent from deployment logs")
        report = {
            "checks": results,
            "scope": "M7.1 deployment controls with optional M7.2 recovery/browser acceptance",
            "live_confirmation": False,
            "release_complete": False,
            "at": datetime.now(UTC).isoformat(),
            "host": platform.platform(),
            "python": platform.python_version(),
            "docker": run(["docker", "version", "--format", "{{.Server.Version}}"]).strip(),
            "revision": run(["git", "rev-parse", "HEAD"]).strip(),
            "working_tree_changes": bool(run(["git", "status", "--porcelain"]).strip()),
        }
        if browser is not None:
            report["browser"] = browser
        if recovery is not None:
            report["recovery"] = recovery
            (ROOT / ".cache/recovery-result.json").write_text(json.dumps(report, indent=2) + "\n")
        (ROOT / ".cache/deployment-result.json").write_text(json.dumps(report, indent=2) + "\n")
        success = True
    finally:
        if success or not options.keep_on_failure:
            run(compose + ["down", "--volumes", "--remove-orphans"])
            shutil.rmtree(directory)
        else:
            print("Retained disposable project for diagnosis: " + str(directory), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
