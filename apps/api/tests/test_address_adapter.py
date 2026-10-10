import json
from pathlib import Path

import pytest
from zecsolve.schemas.address import NormalizeAddressRequest


@pytest.fixture
def address_request(root):
    manifest = json.loads((root / "fixtures/manifest.json").read_text())
    return NormalizeAddressRequest(
        address=manifest["expected"]["receiver_address"], network="mainnet", pool="orchard"
    )


def test_real_normalizer_matches_historical_recovery(root, address_request, report):
    from zecsolve.adapters.address import AddressNormalizer

    result = AddressNormalizer(root / "target/debug/zecsolve-verifier").normalize(address_request)
    assert result.state == "VALID"
    assert result.reason_code == "ADDRESS_NORMALIZED"
    assert result.receiver.receiver_hex == report.output.receiver_hex
    assert result.receiver.pool == report.output.pool
    assert result.receiver.network == report.output.network


def test_invalid_and_missing_receiver_are_not_process_errors(root, address_request):
    from zecsolve.adapters.address import AddressNormalizer

    normalizer = AddressNormalizer(root / "target/debug/zecsolve-verifier")
    invalid = address_request.model_copy(update={"address": "not an address"})
    assert normalizer.normalize(invalid).reason_code == "INVALID_ADDRESS"
    missing = address_request.model_copy(update={"pool": "sapling"})
    result = normalizer.normalize(missing)
    assert (result.state, result.reason_code, result.receiver) == (
        "INVALID",
        "RECEIVER_MISSING",
        None,
    )


def test_missing_executable_is_unavailable(tmp_path, address_request):
    from zecsolve.adapters.address import AddressNormalizer

    result = AddressNormalizer(tmp_path / "absent").normalize(address_request)
    assert (result.state, result.reason_code) == ("UNAVAILABLE", "NORMALIZER_UNAVAILABLE")
    assert result.receiver is None


@pytest.mark.parametrize(
    ("program", "reason"),
    [
        ("import time; time.sleep(5)", "NORMALIZER_TIMEOUT"),
        ("print('x' * 40000)", "NORMALIZER_OUTPUT_TOO_LARGE"),
        ("print('not json')", "NORMALIZER_PROTOCOL_ERROR"),
        ("raise SystemExit(64)", "NORMALIZER_PROCESS_ERROR"),
    ],
)
def test_normalizer_bounds_failures(tmp_path, address_request, program, reason):
    from zecsolve.adapters.address import AddressNormalizer

    binary = tmp_path / "normalizer"
    binary.write_text("#!/usr/bin/python3\n" + program + "\n")
    binary.chmod(0o700)
    result = AddressNormalizer(binary, timeout=0.2).normalize(address_request)
    assert (result.state, result.reason_code, result.receiver) == ("ERROR", reason, None)


@pytest.mark.parametrize(
    "change",
    [
        "result['input_sha256'] = '00' * 32",
        "result['receiver']['pool'] = 'sapling'",
        "result['receiver']['network'] = 'testnet'",
        "result['receiver'] = None",
        "result['schema_version'] = '2'",
        "del result['schema_version']",
        "result['unexpected'] = True",
    ],
)
def test_normalizer_rejects_unbound_or_inconsistent_protocol(tmp_path, address_request, change):
    from zecsolve.adapters.address import AddressNormalizer

    binary = tmp_path / "normalizer"
    binary.write_text(
        "#!/usr/bin/python3\nimport json,sys,hashlib\nfrom pathlib import Path\n"
        "data = Path(sys.argv[3]).read_bytes()\n"
        "result = {'schema_version':'1', 'state':'VALID', 'reason_code':'ADDRESS_NORMALIZED',"
        "'input_sha256':hashlib.sha256(data).hexdigest(), 'receiver':"
        "{'network':'mainnet','pool':'orchard','receiver_hex':'01'*43}}\n"
        + change
        + "\nprint(json.dumps(result))\n"
    )
    binary.chmod(0o700)
    result = AddressNormalizer(binary).normalize(address_request)
    assert (result.state, result.reason_code, result.receiver) == (
        "ERROR",
        "NORMALIZER_PROTOCOL_ERROR",
        None,
    )


def test_request_is_passed_in_private_temporary_file_and_removed(tmp_path, address_request):
    from zecsolve.adapters.address import AddressNormalizer

    record = tmp_path / "observed.json"
    binary = tmp_path / "normalizer"
    binary.write_text(
        "#!/usr/bin/python3\nimport json,sys,stat\nfrom pathlib import Path\n"
        "path = Path(sys.argv[3])\n"
        f"Path({str(record)!r}).write_text(json.dumps({{'argv':sys.argv[1:], "
        "'body':json.loads(path.read_text()), 'path':str(path), "
        "'permissions':stat.S_IMODE(path.parent.stat().st_mode)}))\n"
        "print('not json')\n"
    )
    binary.chmod(0o700)
    AddressNormalizer(binary).normalize(address_request)
    observed = json.loads(record.read_text())
    assert observed["argv"][:2] == ["normalize-address", "--input"]
    assert address_request.address not in observed["argv"]
    assert observed["body"] == address_request.model_dump()
    assert observed["permissions"] == 0o700
    assert not Path(observed["path"]).exists()
