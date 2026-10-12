"""The CI report must never publish Playwright errors or accept skipped coverage."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "browser_acceptance", Path(__file__).resolve().parents[3] / "scripts/browser_acceptance.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def report():
    return {
        "stats": dict(expected=1, unexpected=0, flaky=0, skipped=0, duration=500),
        "errors": [],
        "suites": [
            {
                "specs": [
                    {
                        "title": "public scenario name",
                        "tests": [
                            {
                                "status": "expected",
                                "results": [
                                    {"status": "passed", "stdout": ["private-access-code"]}
                                ],
                                "attachments": ["private-packet"],
                            }
                        ],
                    }
                ]
            }
        ],
    }


def test_retained_browser_report_excludes_raw_diagnostics_and_attachments():
    summary = runner.summarize(report(), 1)
    assert summary["scenarios"] == [{"title": "public scenario name", "status": "passed"}]
    assert "private" not in str(summary)


@pytest.mark.parametrize("failure", ["skipped", "flaky", "unexpected", "empty", "global"])
def test_browser_evidence_rejects_incomplete_or_failed_execution(failure):
    data = report()
    if failure == "global":
        data["errors"] = [{"message": "private-access-code"}]
    elif failure == "empty":
        data["suites"] = []
    else:
        data["stats"]["expected"] = 0
        data["stats"][failure] = 1
    with pytest.raises(RuntimeError) as error:
        runner.summarize(data, 1)
    assert "private-access-code" not in str(error.value)
