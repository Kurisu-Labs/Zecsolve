import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from zecsolve.db.models import Invoice, Merchant

pytestmark = pytest.mark.postgres


def legacy_invoice(merchant, invoice):
    return dict(
        id=invoice,
        merchant_id=merchant,
        network="mainnet",
        pool="orchard",
        expected_zat=200_000,
        expected_receiver="legacy",
        receiver_hex="00" * 43,
        snapshot_hash="ab" * 32,
        policy_version="legacy",
    )


def test_0003_preserves_legacy_terms_without_inventing_policy(database, root):
    from zecsolve.db.models import InvoicePolicy

    merchant, invoice = uuid.uuid4(), uuid.uuid4()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "apps/api/migrations"))
    with database.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0002")
        connection.execute(insert(Merchant).values(id=merchant, name="Existing"))
        # Historical SQL cannot reference columns added in 0003.
        connection.execute(
            text(
                "INSERT INTO invoices (id,merchant_id,network,pool,expected_zat,expected_receiver,"
                "receiver_hex,snapshot_hash,policy_version) VALUES (:id,:merchant_id,:network,"
                ":pool,:expected_zat,:expected_receiver,:receiver_hex,:snapshot_hash,:policy_version)"
            ),
            legacy_invoice(merchant, invoice),
        )
        command.upgrade(config, "head")
        row = (
            connection.execute(select(Invoice.__table__).where(Invoice.id == invoice))
            .mappings()
            .one()
        )
        assert row["snapshot_hash"] == "ab" * 32
        assert row["policy_version"] == "legacy"
        assert row["policy_id"] is None and row["snapshot_version"] is None
        assert connection.execute(select(InvoicePolicy)).first() is None


def test_policy_and_invoice_snapshots_reject_updates_and_deletes(database):
    from zecsolve.db.models import InvoicePolicy

    merchant, invoice, policy = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    with database.begin() as connection:
        connection.execute(insert(Merchant).values(id=merchant, name="Owner"))
        connection.execute(
            insert(InvoicePolicy).values(
                id=policy, merchant_id=merchant, config={"policy_version": "test"}
            )
        )
        connection.execute(
            insert(Invoice).values(
                **legacy_invoice(merchant, invoice), policy_id=policy, snapshot_version="1"
            )
        )
    for table, identity in [(InvoicePolicy, policy), (Invoice, invoice)]:
        for statement in [
            table.__table__.delete().where(table.id == identity),
            update(table).where(table.id == identity).values(id=identity),
        ]:
            with pytest.raises(DBAPIError, match="immutable record"):
                with database.begin() as connection:
                    connection.execute(statement)


def test_invoice_cannot_reference_foreign_policy(database):
    from zecsolve.db.models import InvoicePolicy

    first, second, policy = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    with database.begin() as connection:
        for merchant in [first, second]:
            connection.execute(insert(Merchant).values(id=merchant, name="Owner"))
        connection.execute(insert(InvoicePolicy).values(id=policy, merchant_id=first, config={}))
    with pytest.raises(IntegrityError):
        with database.begin() as connection:
            connection.execute(
                insert(Invoice).values(
                    **legacy_invoice(second, uuid.uuid4()), policy_id=policy, snapshot_version="1"
                )
            )
