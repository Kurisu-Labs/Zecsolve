import base64
import hashlib
import json
import uuid
from datetime import timedelta

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session
from zecsolve.auth import cli
from zecsolve.auth.credentials import (
    authenticate_merchant,
    issue_credential,
    provision_merchant,
    revoke_credential,
)
from zecsolve.config import Settings
from zecsolve.db.models import Merchant, MerchantCredential
from zecsolve.main import create_app

pytestmark = pytest.mark.postgres


@pytest.fixture
def merchant_api(database, root):
    app = create_app(
        Settings(
            _env_file=None,
            poc_token="test-poc-token",
            migrations_path=root / "apps/api/migrations",
            database_url="postgresql+psycopg://unused@127.0.0.1:1/unused",
        )
    )
    app.state.engine.dispose()
    app.state.engine = database
    with TestClient(app) as client:
        yield client


def issue(database, name="Test merchant"):
    with Session(database) as session, session.begin():
        return provision_merchant(session, name)


def headers(issued):
    return {"Authorization": "Bearer " + issued.token}


def test_two_merchants_have_server_derived_identity(database, merchant_api):
    first, second = issue(database, "First"), issue(database, "Second")
    for issued in (first, second):
        response = merchant_api.get(
            "/api/auth/me", headers=headers(issued), params={"merchant_id": str(uuid.uuid4())}
        )
        assert response.status_code == 200
        assert response.json() == {
            "merchant_id": str(issued.merchant_id),
            "credential_id": str(issued.credential_id),
        }
        assert issued.token not in response.text
    assert first.merchant_id != second.merchant_id


def test_database_and_repr_never_store_or_display_token(database):
    issued = issue(database)
    assert issued.token not in repr(issued)
    with Session(database) as session:
        stored = session.get(MerchantCredential, issued.credential_id)
        assert stored.token_sha256 == hashlib.sha256(issued.token.encode()).hexdigest()
        assert stored.token_sha256 != issued.token
        assert stored.merchant_id == issued.merchant_id
        assert stored.expires_at == issued.expires_at


def test_unknown_token_and_poc_token_cannot_authenticate(merchant_api):
    for token in ("zsm_" + "a" * 43, "test-poc-token"):
        response = merchant_api.get("/api/auth/me", headers={"Authorization": "Bearer " + token})
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid merchant credentials"}


def test_expired_token_is_rejected(database, merchant_api):
    issued = issue(database)
    with Session(database) as session, session.begin():
        now = session.scalar(select(func.clock_timestamp()))
        session.execute(
            update(MerchantCredential)
            .where(MerchantCredential.id == issued.credential_id)
            .values(created_at=now - timedelta(days=2), expires_at=now - timedelta(days=1))
        )
    assert merchant_api.get("/api/auth/me", headers=headers(issued)).status_code == 401


def test_revoke_is_immediate_and_idempotent(database, merchant_api):
    issued = issue(database)
    assert merchant_api.get("/api/auth/me", headers=headers(issued)).status_code == 200
    with Session(database) as session, session.begin():
        revoke_credential(session, issued.credential_id)
    with Session(database) as session, session.begin():
        timestamp = session.get(MerchantCredential, issued.credential_id).revoked_at
        revoke_credential(session, issued.credential_id)
    with Session(database) as session:
        assert session.get(MerchantCredential, issued.credential_id).revoked_at == timestamp
    assert merchant_api.get("/api/auth/me", headers=headers(issued)).status_code == 401


def test_rotation_preserves_merchant_and_revokes_only_selected_credential(database, merchant_api):
    original = issue(database)
    with Session(database) as session, session.begin():
        replacement = issue_credential(session, original.merchant_id, ttl_days=1)
        revoke_credential(session, original.credential_id)
    assert replacement.merchant_id == original.merchant_id
    assert replacement.token != original.token
    assert merchant_api.get("/api/auth/me", headers=headers(original)).status_code == 401
    assert merchant_api.get("/api/auth/me", headers=headers(replacement)).status_code == 200


def test_failed_provision_rolls_back_merchant_and_credential(database):
    with pytest.raises(ValueError, match="lifetime"):
        with Session(database) as session, session.begin():
            provision_merchant(session, "Rollback", ttl_days=0)
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(Merchant)) == 0
        assert session.scalar(select(func.count()).select_from(MerchantCredential)) == 0


def test_cli_discloses_once_after_commit_and_revoke_returns_no_token(database, monkeypatch, capsys):
    # Real database/transactions, with only engine construction redirected to the test schema.
    monkeypatch.setattr(cli, "make_engine", lambda settings: database)
    assert cli.main(["create-merchant", "--name", "CLI merchant", "--ttl-days", "1"]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert len(output.out.splitlines()) == 1
    issued = json.loads(output.out)
    with Session(database) as session:
        principal = authenticate_merchant(session, issued["token"])
        assert str(principal.merchant_id) == issued["merchant_id"]
    assert cli.main(["revoke-credential", "--credential-id", issued["credential_id"]]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "credential_id": issued["credential_id"],
        "revoked": True,
    }


def test_cli_failed_commit_discloses_nothing(database, monkeypatch, capsys):
    monkeypatch.setattr(cli, "make_engine", lambda settings: database)
    # A deferred trigger fails at COMMIT, after issuing/flushing the credential.
    with database.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION reject_credential_commit() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'test-only deferred write failure'; END; $$"
            )
        )
        connection.execute(
            text(
                "CREATE CONSTRAINT TRIGGER reject_credential_commit "
                "AFTER INSERT ON merchant_credentials DEFERRABLE INITIALLY DEFERRED "
                "FOR EACH ROW EXECUTE FUNCTION reject_credential_commit()"
            )
        )
    assert cli.main(["create-merchant", "--name", "Rejected"]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "Database operation failed" in output.err
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(Merchant)) == 0


def test_cli_missing_merchant_or_credential_discloses_nothing(database, monkeypatch, capsys):
    monkeypatch.setattr(cli, "make_engine", lambda settings: database)
    assert cli.main(["issue-credential", "--merchant-id", str(uuid.uuid4())]) == 2
    assert capsys.readouterr().out == ""
    assert cli.main(["revoke-credential", "--credential-id", str(uuid.uuid4())]) == 2
    assert capsys.readouterr().out == ""


def test_migration_0002_preserves_existing_merchant(database, root):
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "apps/api/migrations"))
    merchant_id = uuid.uuid4()
    with database.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0001")
        connection.execute(Merchant.__table__.insert().values(id=merchant_id, name="Existing"))
        command.upgrade(config, "head")
        assert (
            connection.scalar(select(Merchant.name).where(Merchant.id == merchant_id)) == "Existing"
        )
        assert connection.scalar(select(func.count()).select_from(MerchantCredential)) == 0


def test_readiness_requires_packaged_head(database, root, monkeypatch):
    # Readiness uses the same engine as authentication, with verifier availability isolated.
    monkeypatch.setattr("zecsolve.main.make_engine", lambda settings: database)
    monkeypatch.setattr("zecsolve.main.VerifierAdapter.available", lambda self: True)
    app = create_app(
        Settings(
            _env_file=None,
            migrations_path=root / "apps/api/migrations",
            evidence_key_id="test",
            evidence_key=base64.b64encode(bytes(32)).decode(),
        )
    )
    with TestClient(app) as api:
        assert api.get("/health/ready").status_code == 200
        config = Config(str(root / "alembic.ini"))
        config.set_main_option("script_location", str(root / "apps/api/migrations"))
        with database.begin() as connection:
            config.attributes["connection"] = connection
            command.downgrade(config, "0001")
        response = api.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["database_migrated"] is False
