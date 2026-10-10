import hashlib
import json

import pytest
from zecsolve.adapters.verifier import VerifierAdapter
from zecsolve.schemas.verification import VerificationReport


def test_mainnet_fixture_recovers_expected_fields(root, report):
    manifest = json.loads((root / "fixtures/manifest.json").read_text())
    expected = manifest["expected"]
    output = report.output
    assert output.txid == expected["txid"]
    assert output.amount_zat == 100_000
    assert output.output_index == 1
    assert output.pool == "orchard"
    assert output.receiver_address == expected["receiver_address"]
    assert bytes.fromhex(output.memo_hex).rstrip(b"\0").decode() == expected["memo_text"]
    assert report.chain_state == "UNAVAILABLE"
    assert report.raw_tx_verified


def test_upstream_artifacts_match_pinned_manifest(root):
    manifest = json.loads((root / "fixtures/manifest.json").read_text())
    for entry in manifest["files"]:
        assert hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]


def test_contract_schema_matches_model(root):
    assert json.loads((root / "contracts/verifier-result.schema.json").read_text()) == (
        VerificationReport.model_json_schema()
    )


def test_tampered_ock_is_invalid_without_recovered_fields(adapter, raw_tx, root):
    result = adapter.verify((root / "fixtures/negative/tampered-ock.json").read_text(), raw_tx)
    assert result.receipt_state == "INVALID"
    assert result.reason_code == "OUTPUT_RECOVERY_FAILED"
    assert result.output is None


@pytest.mark.parametrize(
    ("field", "value", "state", "reason"),
    [
        ("output_index", 9999, "INVALID", "OUTPUT_NOT_FOUND"),
        ("tx_id", "00" * 32, "INVALID", "TXID_MISMATCH"),
        ("version", "999", "UNSUPPORTED", "UNSUPPORTED_RECEIPT_VERSION"),
        ("pool", "future-pool", "UNSUPPORTED", "UNSUPPORTED_POOL"),
        ("network", "testnet", "UNSUPPORTED", "UNSUPPORTED_NETWORK"),
        ("ock", "malformed", "INVALID", "MALFORMED_RECEIPT"),
    ],
)
def test_distinct_failure_reasons(adapter, receipt, raw_tx, field, value, state, reason):
    altered = json.loads(receipt)
    altered[field] = value
    result = adapter.verify(json.dumps(altered), raw_tx)
    assert (result.receipt_state, result.reason_code) == (state, reason)
    assert result.output is None


def test_unknown_consensus_branch_is_unsupported(adapter, receipt, raw_tx):
    raw = bytearray.fromhex(raw_tx.strip())
    raw[8:12] = bytes.fromhex("ffffffff")
    result = adapter.verify(receipt, raw.hex())
    assert result.receipt_state == "UNSUPPORTED"
    assert result.reason_code == "UNSUPPORTED_CONSENSUS_BRANCH"


def test_invalid_transaction_data_does_not_accuse_receipt(adapter, receipt):
    result = adapter.verify(receipt, "invalid hex")
    assert result.receipt_state == "ERROR"
    assert result.reason_code == "MALFORMED_RAW_TRANSACTION"


def test_transaction_with_trailing_bytes_is_rejected(adapter, receipt, raw_tx):
    result = adapter.verify(receipt, raw_tx.strip() + "00")
    assert result.receipt_state == "ERROR"
    assert result.reason_code == "NONCANONICAL_RAW_TRANSACTION"


def test_missing_evidence_and_missing_binary_are_not_invalid(adapter, receipt, raw_tx, tmp_path):
    assert adapter.verify(None, raw_tx).receipt_state == "NONE"
    assert adapter.verify(receipt, None).receipt_state == "UNAVAILABLE"
    assert (
        VerifierAdapter(tmp_path / "absent").verify(receipt, raw_tx).receipt_state == "UNAVAILABLE"
    )


def test_receipt_utf8_byte_limit(adapter, raw_tx):
    assert adapter.verify("é" * 8193, raw_tx).reason_code == "INPUT_TOO_LARGE"


@pytest.mark.parametrize(
    ("program", "reason"),
    [
        ("import time; time.sleep(5)", "VERIFIER_TIMEOUT"),
        ("print('x' * 40000)", "VERIFIER_OUTPUT_TOO_LARGE"),
        ("print('not json')", "VERIFIER_PROTOCOL_ERROR"),
        ("raise SystemExit(1)", "VERIFIER_PROCESS_ERROR"),
    ],
)
def test_subprocess_is_bounded(tmp_path, receipt, raw_tx, program, reason):
    binary = tmp_path / "test-verifier"
    binary.write_text("#!/usr/bin/python3\n" + program + "\n")
    binary.chmod(0o700)
    result = VerifierAdapter(binary, timeout=0.2).verify(receipt, raw_tx)
    assert (result.receipt_state, result.reason_code) == ("ERROR", reason)
