"""Recovery comparisons must tolerate fresh report clocks, never changed history."""

import copy
import importlib.util
import json

import pytest


@pytest.fixture
def recovery_exports(root):
    spec = importlib.util.spec_from_file_location(
        "recovery_exports", root / "scripts/recovery_exports.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_export_comparison_ignores_only_report_generation_time(root, recovery_exports):
    payload = json.loads((root / "fixtures/packets/complete-v2.json").read_text())["payload"]
    original = copy.deepcopy(payload)
    first = recovery_exports.history_digest(payload)
    assert payload == original
    payload["report"]["generated_at"] = "2099-01-01T00:00:00Z"
    assert recovery_exports.history_digest(payload) == first


@pytest.mark.parametrize("field", ["balance", "evidence", "history", "scope"])
def test_export_comparison_detects_changed_persisted_or_disclosed_context(
    root, recovery_exports, field
):
    payload = json.loads((root / "fixtures/packets/complete-v2.json").read_text())["payload"]
    first = recovery_exports.history_digest(payload)
    if field == "balance":
        payload["report"]["balances"]["credited_zat"] += 1
    elif field == "evidence":
        payload["evidence"][0]["receipt"]["data"] += "AA=="
    elif field == "history":
        payload["report"]["events"][0]["event_hash"] = "00" * 32
    else:
        payload["omissions"].append("WITHHELD")
    assert recovery_exports.history_digest(payload) != first
