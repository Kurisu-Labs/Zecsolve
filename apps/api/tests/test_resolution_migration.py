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
