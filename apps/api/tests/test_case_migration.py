import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from zecsolve.db.models import Case, CaseEvent

pytestmark = pytest.mark.postgres


def config(root, connection):
    result = Config(str(root / "alembic.ini"))
    result.set_main_option("script_location", str(root / "apps/api/migrations"))
    result.attributes["connection"] = connection
    return result


def legacy(connection, count=1):
    merchant, invoice = uuid.uuid4(), uuid.uuid4()
    connection.execute(
        text("INSERT INTO merchants(id,name) VALUES (:id,'Legacy')"), {"id": merchant}
    )
    connection.execute(
        text(
            "INSERT INTO invoices (id,merchant_id,network,pool,expected_zat,expected_receiver,"
            "receiver_hex,snapshot_hash,policy_version) VALUES "
            "(:id,:merchant,'mainnet','orchard',1,'legacy',:receiver,:hash,'legacy')"
        ),
        {"id": invoice, "merchant": merchant, "receiver": "00" * 43, "hash": "ab" * 32},
    )
    cases = []
    for _ in range(count):
        case = uuid.uuid4()
        connection.execute(
            text(
                "INSERT INTO cases(id,invoice_id,merchant_id,state,version) "
                "VALUES (:id,:invoice,:merchant,'OPEN',1)"
            ),
            {"id": case, "invoice": invoice, "merchant": merchant},
        )
        cases.append(case)
    return merchant, invoice, cases


def test_duplicate_legacy_cases_block_migration_without_removing_rows(database, root):
    with database.begin() as connection:
        command.downgrade(config(root, connection), "0003")
        _, invoice, _ = legacy(connection, count=2)
    with pytest.raises(RuntimeError, match="duplicate") as error:
        with database.begin() as connection:
            command.upgrade(config(root, connection), "head")
    assert str(invoice) in str(error.value)
    with database.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(Case)) == 2
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0003"


def test_legacy_case_and_event_hashes_are_preserved_without_fabricated_payload(database, root):
    with database.begin() as connection:
        command.downgrade(config(root, connection), "0003")
        _, _, cases = legacy(connection)
        event = uuid.uuid4()
        connection.execute(
            text(
                "INSERT INTO case_events(id,case_id,sequence,actor,action,payload_hash,event_hash) "
                "VALUES (:id,:case,1,'legacy','TEST',:payload,:event)"
            ),
            {"id": event, "case": cases[0], "payload": "ab" * 32, "event": "cd" * 32},
        )
        command.upgrade(config(root, connection), "head")
        row = (
            connection.execute(select(CaseEvent.__table__).where(CaseEvent.id == event))
            .mappings()
            .one()
        )
        assert row["payload_hash"] == "ab" * 32 and row["event_hash"] == "cd" * 32
        assert row["payload"] is None and row["schema_version"] is None
        assert connection.scalar(select(Case.workflow_version).where(Case.id == cases[0])) is None


def test_database_enforces_one_case_per_invoice(database):
    with database.begin() as connection:
        merchant, invoice, _ = legacy(connection)
    with pytest.raises(IntegrityError):
        with database.begin() as connection:
            connection.execute(
                Case.__table__.insert().values(
                    id=uuid.uuid4(),
                    merchant_id=merchant,
                    invoice_id=invoice,
                    state="OPEN",
                    version=1,
                )
            )
