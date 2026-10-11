import hashlib
from datetime import timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from test_persisted_verification import verification_setup as verification_setup
from zecsolve.auth.credentials import issue_credential, revoke_credential
from zecsolve.db.models import BrowserSession
from zecsolve.schemas.grant import GrantCreateRequest
from zecsolve.services.grants import GrantService
from zecsolve.services.workflow import WorkflowError

pytestmark = pytest.mark.postgres


def merchant_code(database, principal):
    with Session(database) as session, session.begin():
        return issue_credential(session, principal.merchant_id)


def test_session_tokens_are_hashed_and_expiry_capped_by_underlying_access(
    database, verification_setup
):
    from zecsolve.services.sessions import SessionService

    _, principal, case, _, _ = verification_setup
    issued = merchant_code(database, principal)
    service = SessionService(database)
    session_result = service.exchange(issued.token)
    assert session_result.token not in repr(
        session_result
    ) and session_result.csrf_token not in repr(session_result)
    info = session_result.info
    assert info.access.role == "merchant" and info.access.credential_id == issued.credential_id
    assert info.expires_at - info.created_at == timedelta(hours=8)
    with Session(database) as session:
        row = session.get(BrowserSession, info.session_id)
        assert row.token_sha256 == hashlib.sha256(session_result.token.encode()).hexdigest()
        assert row.csrf_sha256 == hashlib.sha256(session_result.csrf_token.encode()).hexdigest()
    grant, _ = GrantService(database).create(
        principal,
        case.case_id,
        GrantCreateRequest(scope={"role": "customer"}, ttl_hours=1),
        "customer",
    )
    scoped = service.exchange(grant.access_code)
    assert scoped.info.expires_at == grant.grant.expires_at
    assert scoped.info.access.credential_id is None and scoped.info.access.case_id == case.case_id
    assert "case:resolve" not in scoped.info.access.permissions
    GrantService(database).revoke(principal, case.case_id, grant.grant.grant_id)
    with pytest.raises(WorkflowError) as revoked:
        service.authenticate(scoped.token)
    assert revoked.value.status == 401


def test_credential_revocation_and_logout_invalidate_sessions(database, verification_setup):
    from zecsolve.services.sessions import SessionService

    _, principal, _, _, _ = verification_setup
    issued = merchant_code(database, principal)
    service = SessionService(database)
    first, second = service.exchange(issued.token), service.exchange(issued.token)
    assert first.token != second.token
    service.logout(first.token)
    with pytest.raises(WorkflowError):
        service.authenticate(first.token)
    assert service.authenticate(second.token)[1].session_id == second.info.session_id
    with Session(database) as session, session.begin():
        revoke_credential(session, issued.credential_id)
    with pytest.raises(WorkflowError):
        service.authenticate(second.token)
    with pytest.raises(WorkflowError):
        service.exchange(issued.token)


def test_failed_session_commit_never_returns_tokens(database, verification_setup):
    from sqlalchemy.exc import SQLAlchemyError
    from zecsolve.services.sessions import SessionService

    _, principal, _, _, _ = verification_setup
    issued = merchant_code(database, principal)
    with database.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION fail_session() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'rollback'; END; $$"
            )
        )
        connection.execute(
            text(
                "CREATE CONSTRAINT TRIGGER fail_session AFTER INSERT ON browser_sessions "
                "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION fail_session()"
            )
        )
    with pytest.raises(SQLAlchemyError):
        SessionService(database).exchange(issued.token)
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(BrowserSession)) == 0
