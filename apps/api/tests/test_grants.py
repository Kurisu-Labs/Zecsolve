import hashlib
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from test_persisted_verification import verification_setup as verification_setup
from zecsolve.auth.credentials import MerchantPrincipal, provision_merchant
from zecsolve.db.models import CaseGrant, EvidenceConsent, GrantCreationRequest
from zecsolve.schemas.grant import GrantCreateRequest
from zecsolve.services.workflow import WorkflowError

pytestmark = pytest.mark.postgres


def test_grant_secret_once_hash_only_and_revoke_idempotently(database, verification_setup):
    from zecsolve.services.grants import GrantService

    _, principal, case, _, _ = verification_setup
    service = GrantService(database)
    request = GrantCreateRequest(scope={"role": "customer"})
    issued, replayed = service.create(principal, case.case_id, request, "grant")
    assert not replayed and issued.access_code.startswith("zsg_")
    assert issued.access_code not in repr(issued)
    repeated, replayed = service.create(principal, case.case_id, request, "grant")
    assert replayed and repeated.access_code is None and repeated.grant == issued.grant
    assert issued.access_code not in service.list(principal, case.case_id).model_dump_json()
    with Session(database) as session:
        row = session.get(CaseGrant, issued.grant.grant_id)
        assert row.token_sha256 == hashlib.sha256(issued.access_code.encode()).hexdigest()
    revoked = service.revoke(principal, case.case_id, issued.grant.grant_id)
    assert revoked.revoked_at is not None
    assert service.revoke(principal, case.case_id, issued.grant.grant_id) == revoked
    assert service.create(principal, case.case_id, request, "grant")[0].grant == revoked


def test_reviewer_selection_requires_actual_sharing_consent(database, verification_setup):
    from zecsolve.auth.access import GrantPrincipal, authorize_case_access
    from zecsolve.services.grants import GrantService
    from zecsolve.services.workflow import transaction

    _, principal, case, evidence, _ = verification_setup
    service = GrantService(database)
    request = GrantCreateRequest(
        scope={
            "role": "reviewer",
            "report_sections": ["case", "balances"],
            "evidence_ids": [evidence.evidence_id],
            "allow_export": True,
        }
    )
    with pytest.raises(WorkflowError) as blocked:
        service.create(principal, case.case_id, request, "no-consent")
    assert blocked.value.status == 403
    # Synthetic M4.4 consent fixture; old source labels do not grant sharing rights.
    with Session(database) as session, session.begin():
        session.add(
            EvidenceConsent(
                merchant_id=principal.merchant_id,
                case_id=case.case_id,
                evidence_id=evidence.evidence_id,
                credential_id=principal.credential_id,
                disclosure_version="test-consent",
                processing_authorized=True,
                share_with_reviewers=True,
            )
        )
    created, _ = service.create(principal, case.case_id, request, "consented")
    actor = GrantPrincipal(principal.merchant_id, case.case_id, created.grant.grant_id, "reviewer")
    with transaction(database) as session:
        assert authorize_case_access(session, actor, case.case_id, "case:export").allow_export
        with pytest.raises(WorkflowError):
            authorize_case_access(session, actor, case.case_id, "evidence:read", uuid.uuid4())
    assert (
        service.create(
            principal,
            case.case_id,
            GrantCreateRequest(scope={"role": "reviewer", "report_sections": ["case"]}),
            "report-only",
        )[0].grant.scope.evidence_ids
        == []
    )


def test_concurrent_grant_creation_discloses_one_secret(database, verification_setup):
    from zecsolve.services.grants import GrantService

    _, principal, case, _, _ = verification_setup
    barrier = threading.Barrier(2)

    def create():
        barrier.wait(timeout=5)
        return GrantService(database).create(
            principal, case.case_id, GrantCreateRequest(scope={"role": "customer"}), "same"
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(create) for _ in range(2)]
        results = [f.result(timeout=10) for f in futures]
    assert results[0][0].grant.grant_id == results[1][0].grant.grant_id
    assert sum(item.access_code is not None for item, _ in results) == 1
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(CaseGrant)) == 1


def test_foreign_grants_and_changed_retry_body_are_rejected(database, verification_setup):
    from zecsolve.auth.access import GrantPrincipal
    from zecsolve.services.grants import GrantService

    _, principal, case, _, _ = verification_setup
    service = GrantService(database)
    request = GrantCreateRequest(scope={"role": "customer"})
    created, _ = service.create(principal, case.case_id, request, "key")
    with Session(database) as session, session.begin():
        other = provision_merchant(session, "Other")
    foreign = MerchantPrincipal(other.merchant_id, other.credential_id)
    for call in (
        lambda: service.list(foreign, case.case_id),
        lambda: service.revoke(foreign, case.case_id, created.grant.grant_id),
    ):
        with pytest.raises(WorkflowError) as error:
            call()
        assert error.value.status == 404
    with pytest.raises(WorkflowError) as conflict:
        service.create(principal, case.case_id, request.model_copy(update={"ttl_hours": 48}), "key")
    assert conflict.value.status == 409
    with pytest.raises(WorkflowError) as denied:
        service.list(
            GrantPrincipal(principal.merchant_id, case.case_id, created.grant.grant_id, "customer"),
            case.case_id,
        )
    assert denied.value.status == 403


def test_failed_creation_commit_leaves_no_grant_or_secret_result(database, verification_setup):
    from sqlalchemy.exc import SQLAlchemyError
    from zecsolve.services.grants import GrantService

    _, principal, case, _, _ = verification_setup
    with database.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION fail_grant() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'rollback'; END; $$"
            )
        )
        connection.execute(
            text(
                "CREATE CONSTRAINT TRIGGER fail_grant AFTER INSERT ON grant_creation_requests "
                "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION fail_grant()"
            )
        )
    with pytest.raises(SQLAlchemyError):
        GrantService(database).create(
            principal, case.case_id, GrantCreateRequest(scope={"role": "customer"}), "fail"
        )
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(CaseGrant)) == 0
        assert session.scalar(select(func.count()).select_from(GrantCreationRequest)) == 0


def test_grant_authentication_checks_expiry_revocation_and_role(database, verification_setup):
    from datetime import timedelta

    from zecsolve.auth.access import GrantPrincipal, authorize_grant
    from zecsolve.services.grants import GrantService, authenticate_grant, grant_digest
    from zecsolve.services.workflow import transaction

    _, principal, case, _, _ = verification_setup
    created, _ = GrantService(database).create(
        principal, case.case_id, GrantCreateRequest(scope={"role": "customer"}), "auth"
    )
    with transaction(database) as session:
        actor = authenticate_grant(session, created.access_code)
        assert actor.grant_id == created.grant.grant_id
        with pytest.raises(WorkflowError):
            authorize_grant(
                session,
                GrantPrincipal(principal.merchant_id, case.case_id, actor.grant_id, "reviewer"),
            )
    GrantService(database).revoke(principal, case.case_id, created.grant.grant_id)
    expired_code = "zsg_" + "a" * 43
    with Session(database) as session, session.begin():
        now = session.scalar(select(func.clock_timestamp()))
        session.add(
            CaseGrant(
                merchant_id=principal.merchant_id,
                case_id=case.case_id,
                issued_by=principal.credential_id,
                role="customer",
                token_sha256=grant_digest(expired_code),
                scope={"role": "customer"},
                created_at=now - timedelta(hours=2),
                expires_at=now - timedelta(hours=1),
            )
        )
    with Session(database) as session:
        assert authenticate_grant(session, created.access_code) is None
        assert authenticate_grant(session, expired_code) is None
        assert authenticate_grant(session, "invalid") is None
