import importlib.util

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.postgres


def test_forward_recovery_migration_preserves_populated_legacy_records(database, root):
    spec = importlib.util.spec_from_file_location(
        "rehearse_migration", root / "scripts/rehearse_migration.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with database.connect() as connection:
        before = connection.execute(
            text("SELECT schema_name FROM information_schema.schemata ORDER BY 1")
        ).all()
    result = module.rehearse(database, root)
    assert result["from_revision"] == "0008" and result["to_revision"] == "0009"
    assert result["legacy_allocation_zat"] == 100_000 and result["schema_removed"]
    assert {"claims", "evidence_contents", "output_allocations"} <= set(result["preserved_tables"])
    with database.connect() as connection:
        assert (
            connection.execute(
                text("SELECT schema_name FROM information_schema.schemata ORDER BY 1")
            ).all()
            == before
        )
