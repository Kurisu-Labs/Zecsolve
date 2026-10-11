import pytest
from sqlalchemy import inspect
from test_persisted_verification import verification_setup as verification_setup

pytestmark = pytest.mark.postgres


def test_access_storage_has_scoped_grants_sessions_and_customer_attribution(database):
    names = inspect(database).get_table_names()
    for table in (
        "case_grants",
        "grant_evidence",
        "grant_creation_requests",
        "browser_sessions",
        "evidence_consents",
        "access_submission_requests",
    ):
        assert table in names
    for table in ("claims", "evidence"):
        assert "actor_grant_id" in {col["name"] for col in inspect(database).get_columns(table)}


def test_empty_access_rollback_preserves_existing_encrypted_evidence(
    database, root, verification_setup
):
    from alembic import command
    from alembic.config import Config

    verifier, principal, case, bundle, evidence = verification_setup
    before = evidence.read_content(principal, case.case_id, bundle.evidence_id)
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "apps/api/migrations"))
    with database.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0008")
        command.upgrade(config, "head")
    assert evidence.read_content(principal, case.case_id, bundle.evidence_id) == before


def test_populated_access_rollback_is_blocked(database, root, verification_setup):
    import uuid

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    _, principal, case, _, _ = verification_setup
    with database.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO case_grants "
                "(id, merchant_id, case_id, issued_by, role, token_sha256, scope, expires_at) "
                "VALUES (:id,:merchant,:case,:issuer,'customer',:digest,'{}',now()+interval '1 hour')"
            ),
            dict(
                id=uuid.uuid4(),
                merchant=principal.merchant_id,
                case=case.case_id,
                issuer=principal.credential_id,
                digest="ab" * 32,
            ),
        )
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "apps/api/migrations"))
    with pytest.raises(RuntimeError, match="forward migration"):
        with database.begin() as connection:
            config.attributes["connection"] = connection
            command.downgrade(config, "0008")
