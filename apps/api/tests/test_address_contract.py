import pytest
from pydantic import ValidationError


def test_address_contract_rejects_untrusted_fields_and_invalid_requests():
    from zecsolve.schemas.address import NormalizeAddressRequest

    for fields in (
        {"address": ""},
        {"address": "x" * 1025},
        {"address": "\ud800"},
        {"address": "address", "receiver_hex": "00" * 43},
        {"address": "address", "network": "testnet"},
        {"address": "address", "pool": "transparent"},
    ):
        with pytest.raises(ValidationError):
            NormalizeAddressRequest.model_validate(
                {"network": "mainnet", "pool": "orchard", **fields}
            )


def test_address_result_requires_receiver_only_for_success():
    from zecsolve.schemas.address import AddressNormalizationReport

    receiver = {"network": "mainnet", "pool": "orchard", "receiver_hex": "01" * 43}
    valid = {
        "schema_version": "1",
        "state": "VALID",
        "reason_code": "ADDRESS_NORMALIZED",
        "input_sha256": "ab" * 32,
        "receiver": receiver,
    }
    assert AddressNormalizationReport.model_validate(valid).receiver.receiver_hex == "01" * 43
    for change in (
        {"receiver": None},
        {"state": "INVALID", "reason_code": "INVALID_ADDRESS"},
        {"reason_code": "INVALID_ADDRESS"},
        {"input_sha256": None},
        {"receiver": {**receiver, "receiver_hex": "00"}},
        {"schema_version": "2"},
        {"state": "INVALID", "reason_code": "ADDRESS_NORMALIZED", "receiver": None},
    ):
        with pytest.raises(ValidationError):
            AddressNormalizationReport.model_validate({**valid, **change})
