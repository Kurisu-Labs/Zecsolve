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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-on-failure", action="store_true")
    options = parser.parse_args()
    (ROOT / ".cache").mkdir(exist_ok=True)
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

    def run(args, *, check=True):
        result = subprocess.run(
            args, cwd=ROOT, env=env, capture_output=True, text=True, check=False, timeout=1200
        )
        if check and result.returncode:
            (directory / "command-failure.log").write_text(result.stdout + result.stderr)
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
            return response.status, dict(response.getheaders()), response.read()
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
        logs = run(compose + ["logs", "--no-color"])
        assert all(secret not in logs for secret in (marker, password, key))
        passed("container logs exclude request codes, authorization and configured secrets")
        report = {
            "checks": results,
            "scope": "M7.1 backend preparation; session acceptance pending",
            "at": datetime.now(UTC).isoformat(),
            "host": platform.platform(),
            "python": platform.python_version(),
            "docker": run(["docker", "version", "--format", "{{.Server.Version}}"]).strip(),
            "revision": run(["git", "rev-parse", "HEAD"]).strip(),
            "working_tree_changes": bool(run(["git", "status", "--porcelain"]).strip()),
        }
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
