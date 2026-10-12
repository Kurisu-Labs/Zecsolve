"""Failure artifacts identify public scenarios without publishing private diagnostics."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "browser_acceptance", Path(__file__).resolve().parents[3] / "scripts/browser_acceptance.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
SECRET = "private-access-code-and-packet"


def report(*, simulated=True):
    titles = [t for t in runner.SCENARIOS if ("simulated approval" in t) == simulated]
    return {
        "stats": dict(expected=len(titles), unexpected=0, flaky=0, skipped=0, duration=500),
        "errors": [],
        "suites": [
            {
                "specs": [
                    {
                        "title": title,
                        "file": "workflow.spec.ts",
                        "line": 10,
                        "column": 1,
                        "tests": [
                            {
                                "status": "expected",
                                "expectedStatus": "passed",
                                "results": [
                                    {
                                        "status": "passed",
                                        "retry": 0,
                                        "duration": 100,
                                        "stdout": [SECRET],
                                        "stderr": [SECRET],
                                        "attachments": [{"path": SECRET}],
                                    }
                                ],
                            }
                        ],
                    }
                    for title in titles
                ]
            }
        ],
    }


def result(data):
    return data["suites"][0]["specs"][0]["tests"][0]["results"][0]


def test_retained_browser_report_excludes_raw_diagnostics_and_attachments():
    summary = runner.summarize(report(), 1)
    assert summary["scenarios"][0]["title"] == runner.SCENARIOS[5]
    assert summary["outcome"] == "passed"
    assert SECRET not in json.dumps(summary)


@pytest.mark.parametrize(
    "failure",
    [
        "skipped",
        "flaky",
        "unexpected",
        "empty",
        "global",
        "retry",
        "expected_failure",
        "duplicate",
        "unknown",
    ],
)
def test_browser_evidence_rejects_incomplete_or_failed_execution(failure):
    data = report()
    test = data["suites"][0]["specs"][0]["tests"][0]
    if failure == "global":
        data["errors"] = [{"message": SECRET}]
    elif failure == "empty":
        test["results"] = []
    elif failure == "retry":
        result(data)["retry"] = 1
    elif failure == "expected_failure":
        test["expectedStatus"] = "failed"
        result(data)["status"] = "failed"
    elif failure == "duplicate":
        test["results"] *= 2
    elif failure == "unknown":
        data["suites"][0]["specs"][0]["title"] = SECRET
    else:
        data["stats"]["expected"] = 0
        data["stats"][failure] = 1
    with pytest.raises(RuntimeError) as error:
        runner.summarize(data, 1)
    assert SECRET not in str(error.value)
    assert SECRET not in json.dumps(runner.inspect_report(data, 1))


@pytest.mark.parametrize("value", [SECRET, True, -1, float("nan"), float("inf"), 10**400])
def test_malformed_counts_never_escape_in_exception(value):
    data = report()
    data["stats"]["expected"] = value
    with pytest.raises(RuntimeError) as error:
        runner.summarize(data, 1)
    assert SECRET not in str(error.value)


def test_failure_location_is_projected_without_messages_paths_or_values():
    data = report()
    attempt = result(data)
    attempt.update(status="timedOut", error={"message": SECRET, "stack": SECRET})
    attempt["errors"] = [
        {
            "message": SECRET,
            "location": {"file": str(runner.ROOT / runner.SPEC), "line": 92, "column": 3},
        },
        {"message": SECRET, "location": {"file": "/private/" + SECRET, "line": 1, "column": 1}},
    ]
    summary = runner.inspect_report(data, 1)
    assert summary["outcome"] == "failed"
    assert summary["scenarios"][0]["attempts"][0]["error_locations"] == [
        {"file": runner.SPEC, "line": 92, "column": 3}
    ]
    assert SECRET not in json.dumps(summary)


@pytest.mark.parametrize(
    "failure",
    [
        "exit",
        "exit_with_passing_report",
        "timeout",
        "startup",
        "invalid_json",
        "missing_stats",
        "failed_report",
    ],
)
def test_run_suite_writes_failure_before_raising_and_clears_stale_success(
    tmp_path, monkeypatch, failure
):
    data = report(simulated=False)
    if failure in ("exit", "failed_report"):
        result(data).update(status="failed", errors=[{"message": SECRET}])
    raw = (
        SECRET
        if failure == "invalid_json"
        else json.dumps({} if failure == "missing_stats" else data)
    )
    child = tmp_path / "child.py"
    child.write_text(
        "import sys\nprint("
        + repr(raw)
        + ")\nprint("
        + repr(SECRET)
        + ", file=sys.stderr)\nsys.exit("
        + ("1" if failure.startswith("exit") else "0")
        + ")\n"
    )
    original = subprocess.run

    def invoke(command, **kwargs):
        if command[0] != "node" or command[1] == "--version":
            return original(command, **kwargs)
        assert "--retries=0" in command and "--forbid-only" in command
        if failure == "timeout":
            raise subprocess.TimeoutExpired(SECRET, 600, output=SECRET)
        if failure == "startup":
            raise OSError(SECRET)
        return original([sys.executable, str(child)], **kwargs)

    monkeypatch.setattr(runner.subprocess, "run", invoke)
    retained = tmp_path / "public.json"
    retained.write_text('{"outcome": "passed", "stale": true}')
    with pytest.raises(RuntimeError) as error:
        runner.run_suite(
            tmp_path / "private",
            tmp_path / "state",
            "https://localhost",
            ingress=True,
            result_path=retained,
        )
    public = retained.read_text()
    assert SECRET not in public + str(error.value)
    output = json.loads(public)
    assert output["outcome"] == "failed" and "stale" not in output
    assert output["boundary"] == "packaged-nginx-TLS"
    assert output["live_confirmation"] is False and output["release_complete"] is False
    if failure == "exit":
        assert output["scenarios"][0]["attempts"][0]["status"] == "failed"
    if failure == "exit_with_passing_report":
        assert output["reason"] == "process_failed" and output["exit_code"] == 1


def test_setup_failure_survives_private_cleanup(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["browser_acceptance.py", "--simulated-chain"])
    monkeypatch.setattr(runner, "result_metadata", lambda **kwargs: {"live_confirmation": False})

    def fail(*args, **kwargs):
        raise OSError(SECRET)

    monkeypatch.setattr(runner.subprocess, "Popen", fail)
    with pytest.raises(RuntimeError) as error:
        runner.main()
    output = tmp_path / ".cache/browser-simulated-result.json"
    assert json.loads(output.read_text())["reason"] == "setup_failed"
    assert list(output.parent.iterdir()) == [output]
    assert SECRET not in output.read_text() + str(error.value)


def test_setup_failure_does_not_overwrite_browser_result(tmp_path):
    output = tmp_path / "result.json"
    output.write_text('{"reason":"process_failed"}')
    runner.write_setup_failure(output)
    assert json.loads(output.read_text())["reason"] == "process_failed"
