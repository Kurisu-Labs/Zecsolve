import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from zecsolve.adapters.verifier import VerifierAdapter

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def database(root):
    url = os.getenv("ZECSOLVE_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set ZECSOLVE_TEST_DATABASE_URL to a disposable PostgreSQL database")
    schema = "zecsolve_test_" + uuid.uuid4().hex
    admin = create_engine(url, connect_args={"connect_timeout": 3})
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        url, connect_args={"options": f"-csearch_path={schema}", "connect_timeout": 3}
    )
    try:
        config = Config(str(root / "alembic.ini"))
        config.set_main_option("script_location", str(root / "apps/api/migrations"))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


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
