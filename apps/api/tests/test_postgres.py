"""Run against PostgreSQL, with a fresh, randomly named schema per test."""

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, func, insert, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from zecsolve.db.models import (
    Base,
    Case,
    CaseEvent,
    Evidence,
    Invoice,
    Merchant,
    OutputAllocation,
    Resolution,
    Verification,
)

pytestmark = pytest.mark.postgres


def migration_config(root, connection):
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "apps/api/migrations"))
    config.attributes["connection"] = connection
    return config


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
        url,
        connect_args={
            "options": f"-csearch_path={schema}",
            "connect_timeout": 3,
        },
    )
    try:
        with engine.begin() as connection:
            command.upgrade(migration_config(root, connection), "head")
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            # Only the unique schema created by this test is dropped.
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def seed(engine):
    merchant = uuid.uuid4()
    records = []
    with engine.begin() as connection:
        connection.execute(insert(Merchant).values(id=merchant, name="Synthetic test merchant"))
        for _ in range(2):
            invoice, case, evidence, verification, resolution = [uuid.uuid4() for _ in range(5)]
            connection.execute(
                insert(Invoice).values(
                    id=invoice,
                    merchant_id=merchant,
                    network="mainnet",
                    pool="orchard",
                    expected_zat=100_000,
                    expected_receiver="synthetic",
                    receiver_hex="00" * 43,
                    snapshot_hash="00" * 32,
                    policy_version="test",
                )
            )
            connection.execute(
                insert(Case).values(
                    id=case,
                    invoice_id=invoice,
                    merchant_id=merchant,
                    state="OPEN",
                    version=1,
                )
            )
            connection.execute(
                insert(Evidence).values(
                    id=evidence,
                    case_id=case,
                    type="receipt",
                    source="synthetic-test",
                    sha256="00" * 32,
                    storage_ref="test-only",
                )
            )
            connection.execute(
                insert(Verification).values(
                    id=verification,
                    evidence_id=evidence,
                    receipt_state="VALID",
                    result={},
                    verifier_version="synthetic-test",
                    rules_version="test",
                )
            )
            connection.execute(
                insert(Resolution).values(
                    id=resolution,
                    case_id=case,
                    outcome="PARTIAL_CREDIT",
                    reason="synthetic-test",
                    approved_by="test",
                    approved_at=datetime.now(UTC),
                )
            )
            records.append(
                dict(
                    invoice_id=invoice,
                    verification_id=verification,
                    resolution_id=resolution,
                    case_id=case,
                )
            )
    return records


def allocation(record, index=1):
    return dict(
        network="mainnet",
        pool="orchard",
        txid="ab" * 32,
        output_index=index,
        amount_zat=100_000,
        **{k: v for k, v in record.items() if k != "case_id"},
    )


def test_migration_roundtrip_and_metadata(database, root):
    with database.begin() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        command.downgrade(migration_config(root, connection), "base")
        command.upgrade(migration_config(root, connection), "head")
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001"


def test_concurrent_output_claim_has_exactly_one_winner(database):
    records = seed(database)
    barrier = threading.Barrier(2)

    def compete(record):
        try:
            with database.begin() as connection:
                barrier.wait(timeout=5)
                connection.execute(insert(OutputAllocation).values(**allocation(record)))
            return "credited"
        except IntegrityError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(compete, records)) == ["conflict", "credited"]
    with database.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(OutputAllocation)) == 1


def test_two_outputs_in_one_transaction_can_be_allocated(database):
    records = seed(database)
    with database.begin() as connection:
        for index, record in enumerate(records):
            connection.execute(insert(OutputAllocation).values(**allocation(record, index)))
        assert connection.scalar(select(func.count()).select_from(OutputAllocation)) == 2


def test_snapshots_and_events_reject_edits(database):
    record = seed(database)[0]
    with pytest.raises(DBAPIError, match="immutable record"):
        with database.begin() as connection:
            connection.execute(
                update(Invoice).where(Invoice.id == record["invoice_id"]).values(expected_zat=1)
            )
    event = uuid.uuid4()
    with database.begin() as connection:
        connection.execute(
            insert(CaseEvent).values(
                id=event,
                case_id=record["case_id"],
                sequence=1,
                actor="test",
                action="TEST",
                payload_hash="00" * 32,
                event_hash="11" * 32,
            )
        )
    with pytest.raises(DBAPIError, match="immutable record"):
        with database.begin() as connection:
            connection.execute(update(CaseEvent).where(CaseEvent.id == event).values(action="EDIT"))


def test_case_cannot_reference_another_merchants_invoice(database):
    record = seed(database)[0]
    with pytest.raises(IntegrityError):
        with database.begin() as connection:
            other = uuid.uuid4()
            connection.execute(insert(Merchant).values(id=other, name="Other merchant"))
            connection.execute(
                insert(Case).values(
                    id=uuid.uuid4(),
                    invoice_id=record["invoice_id"],
                    merchant_id=other,
                    state="OPEN",
                    version=1,
                )
            )
