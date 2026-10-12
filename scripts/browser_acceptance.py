"""Run P4's browser scenarios and retain only allowlisted, credential-free results.

The CLI starts P4's isolated HTTPS server. The deployment rehearsal imports
run_suite to exercise the same tests through the actual packaged nginx ingress.
Raw Playwright diagnostics/downloads stay in private temporary storage.
"""

import argparse
import json
import os
import platform
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def summarize(report, expected):
    """Fail closed on empty, skipped, flaky or failed selections; omit raw errors."""
    stats = report["stats"]
    counts = {key: stats[key] for key in ("expected", "unexpected", "flaky", "skipped")}
    if counts != dict(expected=expected, unexpected=0, flaky=0, skipped=0) or report.get("errors"):
        raise RuntimeError(f"Browser acceptance failed: {counts}; private diagnostics withheld")
    scenarios = []

    def visit(suite):
        for spec in suite.get("specs", []):
            for test in spec["tests"]:
                if test["status"] != "expected" or any(
                    result["status"] != "passed" for result in test["results"]
                ):
                    raise RuntimeError("Browser scenario did not pass")
                scenarios.append({"title": spec["title"], "status": "passed"})
        for child in suite.get("suites", []):
            visit(child)

    for suite in report["suites"]:
        visit(suite)
    if len(scenarios) != expected:
        raise RuntimeError("Browser scenario count does not match the required selection")
    return {"counts": counts, "scenarios": scenarios, "duration_ms": stats["duration"]}


def run_suite(directory, state, origin, *, simulated=False, ingress=False):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    env = {
        **os.environ,
        "ZECSOLVE_BROWSER_STATE": str(state),
        "ZECSOLVE_BROWSER_URL": origin,
        "ZECSOLVE_BROWSER_CHANNEL": "chromium",
        "ZECSOLVE_BROWSER_PYTHON": sys.executable,
        # Keep automated fixture setup below the real ingress's 5 requests/sec.
        # No response is mocked and the production limit is not changed.
        "ZECSOLVE_BROWSER_API_INTERVAL_MS": "300" if ingress else "0",
    }
    started = datetime.now(UTC).isoformat()
    command = [
        "node",
        str(ROOT / "apps/web/node_modules/@playwright/test/cli.js"),
        "test",
        "--forbid-only",
        "--retries=0",
        "--reporter=json",
        "--output",
        str(directory / "output"),
        "--grep" if simulated else "--grep-invert",
        "simulated approval",
    ]
    with (
        (directory / "report.json").open("w") as output,
        (directory / "stderr.log").open("w") as errors,
    ):
        result = subprocess.run(
            command, cwd=ROOT / "apps/web", env=env, stdout=output, stderr=errors, timeout=600
        )
    if result.returncode:
        raise RuntimeError("Browser acceptance failed; private diagnostics withheld")
    summary = summarize(json.loads((directory / "report.json").read_text()), 1 if simulated else 8)
    return {
        **summary,
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "boundary": "packaged-nginx-TLS" if ingress else "isolated-FastAPI-TLS",
        "chain_mode": "SIMULATED" if simulated else "OFFLINE",
        "live_confirmation": False,
        "release_complete": False,
        "node": subprocess.check_output(["node", "--version"], text=True).strip(),
        "playwright": json.loads(
            (ROOT / "apps/web/node_modules/@playwright/test/package.json").read_text()
        )["version"],
        "browser_channel": "chromium",
        "api_interval_ms": int(env["ZECSOLVE_BROWSER_API_INTERVAL_MS"]),
        "browser_certificate_verification": "disabled for generated localhost certificate",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulated-chain", action="store_true")
    parser.add_argument("--keep-on-failure", action="store_true")
    options = parser.parse_args()
    (ROOT / ".cache").mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="browser-", dir=ROOT / ".cache"))
    output_path = (
        ROOT
        / ".cache"
        / (
            "browser-simulated-result.json"
            if options.simulated_chain
            else "browser-local-result.json"
        )
    )
    output_path.unlink(missing_ok=True)
    server = None
    success = False
    try:
        command = [sys.executable, str(ROOT / "apps/web/tests/browser_server.py")]
        if options.simulated_chain:
            command.append("--simulated-chain")
        with (directory / "server.log").open("w") as log:
            server = subprocess.Popen(
                command,
                cwd=ROOT,
                env={**os.environ, "ZECSOLVE_BROWSER_SCRATCH": str(directory)},
                stdout=log,
                stderr=log,
            )
        for _ in range(60):
            if server.poll() is not None:
                raise RuntimeError("Browser server exited; private diagnostics withheld")
            if (directory / "tls.crt").exists():
                context = ssl.create_default_context(cafile=str(directory / "tls.crt"))
                try:
                    with urllib.request.urlopen(
                        "https://localhost:8443/health/ready", context=context, timeout=2
                    ) as response:
                        if response.status == 200:
                            break
                except (OSError, urllib.error.URLError):
                    pass
            time.sleep(1)
        else:
            raise RuntimeError("Browser server did not become ready")
        report = run_suite(
            directory / "playwright",
            directory / "state.json",
            "https://localhost:8443",
            simulated=options.simulated_chain,
        )
        report.update(
            revision=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            working_tree_changes=bool(
                subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
            ),
            host=platform.platform(),
            python=platform.python_version(),
        )
        output_path.write_text(json.dumps(report, indent=2) + "\n")
        success = True
        print(f"PASS: {report['counts']['expected']} {report['chain_mode']} browser scenarios")
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        if success or not options.keep_on_failure:
            shutil.rmtree(directory)
        else:
            print("Private browser diagnostics retained: " + str(directory))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
