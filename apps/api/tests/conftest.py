from pathlib import Path

import pytest
from zecsolve.adapters.verifier import VerifierAdapter

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def root():
    return ROOT


@pytest.fixture
def receipt():
    return (ROOT / "fixtures/mainnet/receipt.json").read_text()


@pytest.fixture
def raw_tx():
    return (ROOT / "fixtures/mainnet/transaction.hex").read_text()


@pytest.fixture
def adapter():
    instance = VerifierAdapter(ROOT / "target/debug/zecsolve-verifier")
    assert instance.available(), "Build the real verifier first: cargo build --locked"
    return instance


@pytest.fixture
def report(adapter, receipt, raw_tx):
    result = adapter.verify(receipt, raw_tx)
    assert result.receipt_state == "VALID", result.reason_code
    return result
