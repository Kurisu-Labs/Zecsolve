import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from test_persisted_verification import verification_setup as verification_setup
from zecsolve.db.models import BrowserSession, CaseGrant
from zecsolve.services.workflow import WorkflowError, transaction

pytestmark = pytest.mark.postgres


def seed_grant(database, principal, case, role="customer", **changes):
    scope = dict(
        role=role,
        report_sections=["case", "balances"] if role == "reviewer" else [],
        evidence_ids=[],
        allow_export=False,
    )
    with Session(database) as session, session.begin():
        now = session.scalar(select(func.clock_timestamp()))
        row = CaseGrant(
            id=uuid.uuid4(),
            merchant_id=principal.merchant_id,
            case_id=case.case_id,
            issued_by=principal.credential_id,
            role=role,
            token_sha256=uuid.uuid4().hex * 2,
            scope=scope,
            created_at=now,
            expires_at=now + timedelta(hours=1),
            **changes,
        )
        session.add(row)
        session.flush()
        return row.id


def test_customer_and_reviewer_permissions_are_case_scoped(database, verification_setup):
    from zecsolve.auth.access import GrantPrincipal, authorize_case_access

    _, merchant, case, _, _ = verification_setup
    for role, allowed, denied in [
        ("customer", "evidence:submit", "case:resolve"),
        ("reviewer", "report:read", "evidence:submit"),
    ]:
        grant_id = seed_grant(database, merchant, case, role)
        actor = GrantPrincipal(merchant.merchant_id, case.case_id, grant_id, role)
        with transaction(database) as session:
            context = authorize_case_access(session, actor, case.case_id, allowed)
            assert context.credential_id is None and context.grant_id == grant_id
            with pytest.raises(WorkflowError) as error:
                authorize_case_access(session, actor, case.case_id, denied)
            assert error.value.status == 403
            with pytest.raises(WorkflowError) as foreign:
                authorize_case_access(session, actor, uuid.uuid4(), allowed)
            assert foreign.value.status == 404
        with database.begin() as connection:
            connection.execute(
                update(CaseGrant)
                .where(CaseGrant.id == grant_id)
                .values(revoked_at=func.clock_timestamp())
            )
        with transaction(database) as session, pytest.raises(WorkflowError) as revoked:
            authorize_case_access(session, actor, case.case_id, allowed)
        assert revoked.value.status == 401


def test_session_does_not_outlive_its_grant_and_cannot_change_actor(database, verification_setup):
    from zecsolve.auth.access import GrantPrincipal, authorize_case_access

    _, merchant, case, _, _ = verification_setup
    grant_id = seed_grant(database, merchant, case)
    with Session(database) as session, session.begin():
        now = session.scalar(select(func.clock_timestamp()))
        session_id = uuid.uuid4()
        session.add(
            BrowserSession(
                id=session_id,
                merchant_id=merchant.merchant_id,
                grant_id=grant_id,
                case_id=case.case_id,
                token_sha256="ab" * 32,
                csrf_sha256="cd" * 32,
                created_at=now,
                expires_at=now + timedelta(hours=2),
            )
        )
    actor = GrantPrincipal(merchant.merchant_id, case.case_id, grant_id, "customer", session_id)
    with transaction(database) as session:
        assert (
            authorize_case_access(session, actor, case.case_id, "claim:submit").session_id
            == session_id
        )
    with database.begin() as connection:
        connection.execute(
            update(BrowserSession)
            .where(BrowserSession.id == session_id)
            .values(revoked_at=func.clock_timestamp())
        )
    with transaction(database) as session, pytest.raises(WorkflowError):
        authorize_case_access(session, actor, case.case_id, "claim:submit")


def test_grant_expiry_is_rechecked_after_waiting_for_session(database, verification_setup):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from zecsolve.auth.access import GrantPrincipal, authorize_case_access

    _, merchant, case, _, _ = verification_setup
    with Session(database) as session, session.begin():
        now = session.scalar(select(func.clock_timestamp()))
        grant_id, session_id = uuid.uuid4(), uuid.uuid4()
        session.add(
            CaseGrant(
                id=grant_id,
                merchant_id=merchant.merchant_id,
                case_id=case.case_id,
                issued_by=merchant.credential_id,
                role="customer",
                token_sha256="ef" * 32,
                scope=dict(role="customer"),
                created_at=now - timedelta(seconds=1),
                expires_at=now + timedelta(seconds=0.3),
            )
        )
        session.flush()
        session.add(
            BrowserSession(
                id=session_id,
                merchant_id=merchant.merchant_id,
                case_id=case.case_id,
                grant_id=grant_id,
                token_sha256="12" * 32,
                csrf_sha256="34" * 32,
                created_at=now,
                expires_at=now + timedelta(hours=1),
            )
        )
    actor = GrantPrincipal(merchant.merchant_id, case.case_id, grant_id, "customer", session_id)
    entered = threading.Event()

    def authorize():
        with transaction(database) as session:
            entered.set()
            try:
                authorize_case_access(session, actor, case.case_id, "claim:submit")
                return "allowed"
            except WorkflowError as error:
                return error.status

    with database.begin() as connection:
        connection.execute(
            select(BrowserSession.id).where(BrowserSession.id == session_id).with_for_update()
        )
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(authorize)
            assert entered.wait(timeout=2)
            from sqlalchemy import text

            connection.execute(text("SELECT pg_sleep(0.4)"))
            connection.commit()
            assert future.result(timeout=5) == 401


def test_customer_attribution_needs_no_merchant_credential_and_access_is_revoke_only(
    database, verification_setup
):
    from sqlalchemy.exc import DBAPIError
    from zecsolve.db.models import Claim

    _, merchant, case, _, _ = verification_setup
    grant_id = seed_grant(database, merchant, case)
    with Session(database) as session, session.begin():
        claim = Claim(
            case_id=case.case_id,
            merchant_id=merchant.merchant_id,
            actor_grant_id=grant_id,
            claimant_role="customer",
            note="Synthetic attribution",
        )
        session.add(claim)
        session.flush()
        assert claim.actor_credential_id is None
    for statement in (update(CaseGrant).values(role="reviewer"), CaseGrant.__table__.delete()):
        with pytest.raises(DBAPIError, match="immutable access record"):
            with database.begin() as connection:
                connection.execute(statement)
