import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

pytestmark = pytest.mark.postgres


def test_resolution_schema_roundtrip_preserves_legacy_tables(database, root):
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "apps/api/migrations"))
    assert "decision_evaluations" in inspect(database).get_table_names()
    with database.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0006")
        assert "resolutions" in inspect(connection).get_table_names()
        assert "outcome_snapshot" not in {
            c["name"] for c in inspect(connection).get_columns("resolutions")
        }
        command.upgrade(config, "head")
    assert "case_resolution_requests" in inspect(database).get_table_names()


def test_legacy_resolutions_and_allocations_survive_without_invented_decisions(database, root):
    from sqlalchemy import insert, select
    from test_postgres import allocation, seed
    from zecsolve.db.models import OutputAllocation, Resolution

    records = seed(database)
    with database.begin() as connection:
        connection.execute(insert(OutputAllocation).values(**allocation(records[0])))
        before = connection.execute(select(Resolution.__table__)).mappings().all()
        config = Config(str(root / "alembic.ini"))
        config.set_main_option("script_location", str(root / "apps/api/migrations"))
        config.attributes["connection"] = connection
        command.downgrade(config, "0006")
        command.upgrade(config, "head")
        after = connection.execute(select(Resolution.__table__)).mappings().all()
        assert before == after and all(row["outcome_snapshot"] is None for row in after)
        row = connection.execute(select(OutputAllocation.__table__)).mappings().one()
        assert (
            row["merchant_id"] is None and row["case_id"] is None and row["amount_zat"] == 100_000
        )
