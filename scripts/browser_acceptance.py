"""Run P4's browser scenarios and retain only allowlisted, credential-free results.

The CLI starts P4's isolated HTTPS server. The deployment rehearsal imports
run_suite to exercise the same tests through the actual packaged nginx ingress.
Raw Playwright diagnostics/downloads stay in private temporary storage.
"""

import argparse
import json
import math
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


# Only these public, reviewed scenario names may leave the private report.
SCENARIOS = (
    "three roles complete the real HTTPS submission and merchant review flow",
    "mobile login, invalid access and explicitly selected demo",
    "merchant sees tampered and missing evidence without credit",
    "stale merchant decisions refresh for explicit review and noncredit decisions retry safely",
    "lost grant creation responses expose no replacement secret",
    "simulated approval retries once and a second invoice cannot reuse its output",
    "keyboard and accessibility checks cover login, invoice and scoped submission on mobile",
    "case listing paginates and filters the server summaries",
    "local expiry returns to login and missing CSRF can recover with a new session",
)
SPEC = "apps/web/tests/browser/workflow.spec.ts"
STATUSES = {"passed", "failed", "timedOut", "skipped", "interrupted"}


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1e9:
        raise ValueError("Invalid numeric report field")
    return value


def location(value):
    """Keep coordinates in our known spec only; never expose arbitrary paths."""
    if not isinstance(value, dict) or value.get("file") not in (
        "workflow.spec.ts",
        SPEC,
        str(ROOT / SPEC),
    ):
        return None
    line, column = value.get("line"), value.get("column")
    if type(line) is int and type(column) is int and 0 < line < 50000 and 0 < column < 10000:
        return {"file": SPEC, "line": line, "column": column}
    return None


def inspect_report(report, expected):
    """Project untrusted JSON onto fixed names/enums/numbers, including failures."""
    counts = {
        key: number(report["stats"][key]) for key in ("expected", "unexpected", "flaky", "skipped")
    }
    scenarios = []

    def visit(suite):
        for spec in suite.get("specs", []):
            title = spec["title"] if spec["title"] in SCENARIOS else "unknown scenario"
            for test in spec["tests"]:
                attempts = []
                for result in test["results"]:
                    locations = []
                    for error in [(result.get("error") or {}), *result.get("errors", [])]:
                        loc = location(error.get("location"))
                        if loc and loc not in locations:
                            locations.append(loc)
                    loc = location(result.get("errorLocation"))
                    if loc and loc not in locations:
                        locations.append(loc)
                    attempts.append(
                        {
                            "status": result["status"]
                            if result["status"] in STATUSES
                            else "unknown",
                            "retry": number(result["retry"]),
                            "duration_ms": number(result["duration"]),
                            "error_locations": locations,
                        }
                    )
                passed = (
                    title != "unknown scenario"
                    and location(spec) is not None
                    and test["status"] == "expected"
                    and test["expectedStatus"] == "passed"
                    and len(attempts) == 1
                    and attempts[0]["status"] == "passed"
                    and attempts[0]["retry"] == 0
                    and not any(r.get("error") or r.get("errors") for r in test["results"])
                )
                scenarios.append(
                    {
                        "title": title,
                        "location": location(spec),
                        "status": "passed" if passed else "failed",
                        "attempts": attempts,
                    }
                )
        for child in suite.get("suites", []):
            visit(child)

    for suite in report["suites"]:
        visit(suite)
    required = {s for s in SCENARIOS if ("simulated approval" in s) == (expected == 1)}
    passed = (
        counts == dict(expected=expected, unexpected=0, flaky=0, skipped=0)
        and not report.get("errors")
        and len(scenarios) == expected
        and {s["title"] for s in scenarios} == required
        and all(s["status"] == "passed" for s in scenarios)
    )
    return {
        "outcome": "passed" if passed else "failed",
        "counts": counts,
        "scenarios": scenarios,
        "duration_ms": number(report["stats"]["duration"]),
        "global_error_count": len(report.get("errors", [])),
    }


def summarize(report, expected):
    """Fail closed on malformed, empty, skipped, flaky or failed selections."""
    try:
        summary = inspect_report(report, expected)
    except (KeyError, TypeError, ValueError, AttributeError, RecursionError, OverflowError):
        raise RuntimeError("Invalid browser report; private diagnostics withheld") from None
    if summary["outcome"] != "passed":
        raise RuntimeError("Browser acceptance failed; private diagnostics withheld")
    return summary


def result_metadata(*, simulated=False, ingress=False):
    try:
        node = subprocess.check_output(
            ["node", "--version"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        playwright = json.loads(
            (ROOT / "apps/web/node_modules/@playwright/test/package.json").read_text()
        )["version"]
    except (OSError, subprocess.SubprocessError, ValueError, KeyError):
        node, playwright = "unavailable", "unavailable"
    return {
        "node": node,
        "playwright": playwright,
        "schema_version": 1,
        "boundary": "packaged-nginx-TLS" if ingress else "isolated-FastAPI-TLS",
        "chain_mode": "SIMULATED" if simulated else "OFFLINE",
        "live_confirmation": False,
        "release_complete": False,
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "working_tree_changes": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        ),
        "host": platform.platform(),
        "python": platform.python_version(),
    }


def write_result(path, report):
    if path is not None:
        path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


def write_setup_failure(path, *, simulated=False, ingress=False):
    # Preserve a more specific browser failure if run_suite already wrote one.
    if not path.exists():
        write_result(
            path,
            {
                **result_metadata(simulated=simulated, ingress=ingress),
                "outcome": "failed",
                "reason": "setup_failed",
                "finished_at": datetime.now(UTC).isoformat(),
            },
        )


def run_suite(directory, state, origin, *, simulated=False, ingress=False, result_path=None):
    if result_path is not None:
        result_path.unlink(missing_ok=True)
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
    reason = "completed"
    exit_code = None
    try:
        with (
            (directory / "report.json").open("w") as output,
            (directory / "stderr.log").open("w") as errors,
        ):
            result = subprocess.run(
                command, cwd=ROOT / "apps/web", env=env, stdout=output, stderr=errors, timeout=600
            )
        exit_code = result.returncode
        if exit_code:
            reason = "process_failed"
    except subprocess.TimeoutExpired:
        reason = "runner_timeout"
    except OSError:
        reason = "process_start_failed"
    summary = {"outcome": "failed", "counts": None, "scenarios": []}
    try:
        summary = inspect_report(
            json.loads((directory / "report.json").read_text()), 1 if simulated else 8
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        RecursionError,
        OverflowError,
    ):
        if reason == "completed":
            reason = "invalid_report"
    if reason != "completed" or summary["outcome"] != "passed":
        summary["outcome"] = "failed"
        if reason == "completed":
            reason = "acceptance_failed"
    report = {
        **result_metadata(simulated=simulated, ingress=ingress),
        **summary,
        "reason": reason,
        "exit_code": exit_code,
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "browser_channel": "chromium",
        "api_interval_ms": int(env["ZECSOLVE_BROWSER_API_INTERVAL_MS"]),
        "browser_certificate_verification": "disabled for generated localhost certificate",
    }
    # Save before raising or cleanup; stdout/stderr/error messages never leave directory.
    write_result(result_path, report)
    if report["outcome"] != "passed":
        raise RuntimeError(
            "Browser acceptance failed; see sanitized result, private diagnostics withheld"
        )
    return report


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
            result_path=output_path,
        )
        success = True
        print(f"PASS: {report['counts']['expected']} {report['chain_mode']} browser scenarios")
    except Exception:
        write_setup_failure(output_path, simulated=options.simulated_chain)
        raise RuntimeError(
            "Browser run failed; see sanitized result, private diagnostics withheld"
        ) from None
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
