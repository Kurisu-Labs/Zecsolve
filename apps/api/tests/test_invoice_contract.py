import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError


def fields(**changes):
    return dict(
        expected_zat=200_000,
        network="mainnet",
        pool="orchard",
        receiver_address="u1example",
        **changes,
    )


@pytest.mark.parametrize("amount", [0, -1, True, 0.01, "200000", 2_100_000_000_000_001])
def test_invoice_requires_positive_integer_zatoshis(amount):
    from zecsolve.schemas.invoice import InvoiceCreateRequest

    with pytest.raises(ValidationError):
        InvoiceCreateRequest.model_validate({**fields(), "expected_zat": amount})


@pytest.mark.parametrize(
    "extra",
    [
        {"merchant_id": "untrusted"},
        {"receiver_hex": "00" * 43},
        {"policy": {}},
        {"unique_receiver_binding": True},
    ],
)
def test_invoice_cannot_supply_identity_normalized_bytes_or_policy(extra):
    from zecsolve.schemas.invoice import InvoiceCreateRequest

    with pytest.raises(ValidationError):
        InvoiceCreateRequest.model_validate({**fields(), **extra})


def test_memo_preserves_original_text_and_pads_utf8_bytes():
    from zecsolve.schemas.invoice import InvoiceCreateRequest

    request = InvoiceCreateRequest(**fields(expected_memo="é" * 256))
    assert request.expected_memo == "é" * 256
    assert request.memo_bytes == ("é" * 256).encode()
    assert InvoiceCreateRequest(**fields(expected_memo="x")).memo_bytes == b"x" + bytes(511)
    assert InvoiceCreateRequest(**fields(expected_memo="")).memo_bytes == bytes(512)
    assert InvoiceCreateRequest(**fields()).memo_bytes is None
    for memo in ["é" * 257, "\ud800", "embedded\0nul"]:
        with pytest.raises(ValidationError):
            InvoiceCreateRequest(**fields(expected_memo=memo))


def test_expiry_requires_timezone_and_normalizes_to_utc():
    from zecsolve.schemas.invoice import InvoiceCreateRequest

    first = InvoiceCreateRequest(**fields(expires_at="2026-10-12T07:00:00+07:00"))
    second = InvoiceCreateRequest(**fields(expires_at="2026-10-12T00:00:00Z"))
    assert first.expires_at == datetime(2026, 10, 12, tzinfo=UTC)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    for expiry in ["2026-10-12T00:00:00", 1791763200, "1791763200"]:
        with pytest.raises(ValidationError):
            InvoiceCreateRequest(**fields(expires_at=expiry))


def test_policy_defaults_are_conservative_and_immutable():
    from zecsolve.schemas.invoice import InvoicePolicyV1

    policy = InvoicePolicyV1()
    assert policy.minimum_confirmations == 10
    assert policy.max_observation_age_seconds == 60
    assert policy.memo_binding == "exact"
    assert policy.allow_overpayment is False
    assert policy.unique_receiver_binding is False
    with pytest.raises(ValidationError):
        policy.minimum_confirmations = 0


def test_invoice_schemas_match_runtime_models(root):
    from zecsolve.schemas.invoice import InvoiceCreateRequest, InvoiceSnapshotV1

    for name, model in (
        ("invoice-create-request", InvoiceCreateRequest),
        ("invoice-snapshot", InvoiceSnapshotV1),
    ):
        assert (
            json.loads((root / f"contracts/{name}.schema.json").read_text())
            == model.model_json_schema()
        )
