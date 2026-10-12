"""Release evidence must fail closed and never publish child diagnostics."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "rehearse_release", Path(__file__).resolve().parents[3] / "scripts/rehearse_release.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.mark.parametrize("mode", ["failure", "timeout", "invalid-json"])
def test_child_failure_does_not_expose_private_output(monkeypatch, mode):
    def execute(*args, **kwargs):
        if mode == "timeout":
            raise subprocess.TimeoutExpired(args[0], 60, output=b"private-db-url")
        return subprocess.CompletedProcess(
            args[0], 1 if mode == "failure" else 0, b"private-db-url", b"private-token"
        )

    monkeypatch.setattr(runner.subprocess, "run", execute)
    with pytest.raises(RuntimeError) as error:
        runner.run_json(["demo"])
    assert "private" not in str(error.value)


def test_failed_run_removes_previous_success_report(tmp_path, monkeypatch):
    output = tmp_path / "report.json"
    output.write_text('{"status": "passed"}')
    monkeypatch.setattr(runner, "OUTPUT", output)

    def fail(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(runner, "run_json", fail)
    with pytest.raises(RuntimeError):
        runner.main()
    assert not output.exists()


@pytest.mark.postgres
def test_release_rehearsal_records_actual_scenarios_and_replay(root, tmp_path):
    if not os.getenv("ZECSOLVE_TEST_DATABASE_URL"):
        pytest.skip("Disposable PostgreSQL required")
    original_examples = (root / "fixtures/packets/replay-results.json").read_bytes()
    # Separate the test output from the CI artifact produced by the documented CLI.
    runner.OUTPUT = tmp_path / "rehearsal.json"
    try:
        assert runner.main() == 0
        report = json.loads(runner.OUTPUT.read_text())
    finally:
        runner.OUTPUT = root / ".cache/release-rehearsal.json"
    assert len(report["scenarios"]) == 3
    assert report["replay"]["complete-v2"]["status"] == "REPRODUCED"
    assert {name: entry["exit_code"] for name, entry in report["replay"].items()} == {
        "complete-v1": 0,
        "complete-v2": 0,
        "tampered": 1,
        "scoped": 2,
        "missing-version": 2,
        "unsupported-version": 3,
    }
    assert report["schema_removed"] is True
    assert report["live_confirmation"] is False and report["release_complete"] is False
    assert (root / "fixtures/packets/replay-results.json").read_bytes() == original_examples
    poc = runner.run_json([sys.executable, "scripts/poc.py"])
    demo = runner.run_json([sys.executable, "scripts/demo_resolution.py"])
    demo["private_token"] = "do-not-retain"
    assert "do-not-retain" not in str(runner.check_scenarios(poc, demo))
    for field, bad_value in [
        ("live_confirmation", True),
        ("schema_removed", False),
        ("retry_same_resolution", False),
        ("rejected_invoice_credited_zat", 100_000),
        ("source_kind", "RPC"),
        ("second_invoice", "APPROVED"),
    ]:
        with pytest.raises(RuntimeError):
            runner.check_scenarios(poc, demo | {field: bad_value})
