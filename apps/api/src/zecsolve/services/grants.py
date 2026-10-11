import hashlib
import re
import secrets
from datetime import timedelta

from sqlalchemy import func, select, update

from zecsolve.auth.access import GrantPrincipal, sharing_allowed
from zecsolve.db.models import Case, CaseGrant, Evidence, GrantCreationRequest, GrantEvidence
from zecsolve.domain.snapshots import digest
from zecsolve.schemas.access import GrantScopeV1
from zecsolve.schemas.grant import GrantCreatedV1, GrantListV1, GrantMetadataV1
from zecsolve.services.cases import load_owned_case
from zecsolve.services.workflow import (
    WorkflowError,
    authorize_merchant,
    transaction,
    validate_idempotency_key,
)


def grant_digest(code):
    if not isinstance(code, str) or not re.fullmatch(r"zsg_[A-Za-z0-9_-]{43}", code):
        return None
    return hashlib.sha256(code.encode("ascii")).hexdigest()


def authenticate_grant(session, code):
    hashed = grant_digest(code)
    if hashed is None:
        return None
    row = session.scalar(
        select(CaseGrant).where(
            CaseGrant.token_sha256 == hashed,
            CaseGrant.revoked_at.is_(None),
            CaseGrant.expires_at > func.clock_timestamp(),
        )
    )
    return GrantPrincipal(row.merchant_id, row.case_id, row.id, row.role) if row else None


def metadata(session, row):
    try:
        scope = GrantScopeV1.model_validate(row.scope)
        selections = set(
            session.scalars(
                select(GrantEvidence.evidence_id).where(GrantEvidence.grant_id == row.id)
            )
        )
        if scope.role != row.role or selections != set(scope.evidence_ids):
            raise ValueError("Inconsistent grant selection")
        return GrantMetadataV1(
            grant_id=row.id,
            case_id=row.case_id,
            merchant_id=row.merchant_id,
            issued_by=row.issued_by,
            scope=scope,
            created_at=row.created_at,
            expires_at=row.expires_at,
            revoked_at=row.revoked_at,
        )
    except ValueError:
        raise WorkflowError(409, "GRANT_SCOPE_UNAVAILABLE") from None


class GrantService:
    def __init__(self, engine):
        self.engine = engine

    def create(self, principal, case_id, request, key):
        code = None
        with transaction(self.engine) as session:
            authorize_merchant(session, principal)
            key = validate_idempotency_key(key)
            load_owned_case(session, principal, case_id)
            session.execute(
                select(Case.id).where(Case.id == case_id).with_for_update()
            ).scalar_one()
            authorize_merchant(session, principal)
            request_hash = digest(request.model_dump(mode="json"))
            previous = session.scalar(
                select(GrantCreationRequest).where(
                    GrantCreationRequest.merchant_id == principal.merchant_id,
                    GrantCreationRequest.credential_id == principal.credential_id,
                    GrantCreationRequest.case_id == case_id,
                    GrantCreationRequest.idempotency_key == key,
                )
            )
            if previous is not None:
                if previous.request_hash != request_hash:
                    raise WorkflowError(409, "IDEMPOTENCY_CONFLICT")
                row = session.get(CaseGrant, previous.grant_id)
                if row is None or (row.merchant_id, row.case_id) != (
                    principal.merchant_id,
                    case_id,
                ):
                    raise WorkflowError(409, "GRANT_HISTORY_UNAVAILABLE")
                result = GrantCreatedV1(grant=metadata(session, row))
                replayed = True
            else:
                for evidence_id in request.scope.evidence_ids:
                    owned = session.scalar(
                        select(Evidence.id).where(
                            Evidence.id == evidence_id,
                            Evidence.case_id == case_id,
                            Evidence.merchant_id == principal.merchant_id,
                        )
                    )
                    if owned is None:
                        raise WorkflowError(404, "EVIDENCE_NOT_FOUND")
                    if not sharing_allowed(session, principal.merchant_id, case_id, evidence_id):
                        raise WorkflowError(403, "EVIDENCE_SHARING_NOT_AUTHORIZED")
                now = session.scalar(select(func.clock_timestamp()))
                code = "zsg_" + secrets.token_urlsafe(32)
                row = CaseGrant(
                    merchant_id=principal.merchant_id,
                    case_id=case_id,
                    issued_by=principal.credential_id,
                    role=request.scope.role,
                    token_sha256=grant_digest(code),
                    scope=request.scope.model_dump(mode="json"),
                    created_at=now,
                    expires_at=now + timedelta(hours=request.ttl_hours),
                )
                session.add(row)
                session.flush()
                for evidence_id in request.scope.evidence_ids:
                    session.add(
                        GrantEvidence(
                            grant_id=row.id,
                            evidence_id=evidence_id,
                            case_id=case_id,
                            merchant_id=principal.merchant_id,
                        )
                    )
                session.add(
                    GrantCreationRequest(
                        merchant_id=principal.merchant_id,
                        credential_id=principal.credential_id,
                        case_id=case_id,
                        grant_id=row.id,
                        idempotency_key=key,
                        request_hash=request_hash,
                    )
                )
                session.flush()
                result = GrantCreatedV1(grant=metadata(session, row))
                replayed = False
            authorize_merchant(session, principal)
        # Disclose only after the transaction commits; replay cannot recover this value.
        return result.model_copy(update={"access_code": code}), replayed

    def list(self, principal, case_id):
        with transaction(self.engine) as session:
            authorize_merchant(session, principal)
            load_owned_case(session, principal, case_id)
            items = [
                metadata(session, row)
                for row in session.scalars(
                    select(CaseGrant)
                    .where(
                        CaseGrant.merchant_id == principal.merchant_id, CaseGrant.case_id == case_id
                    )
                    .order_by(CaseGrant.created_at.desc(), CaseGrant.id.desc())
                )
            ]
            authorize_merchant(session, principal)
            return GrantListV1(items=items)

    def revoke(self, principal, case_id, grant_id):
        with transaction(self.engine) as session:
            authorize_merchant(session, principal)
            load_owned_case(session, principal, case_id)
            row = session.scalar(
                select(CaseGrant)
                .where(
                    CaseGrant.id == grant_id,
                    CaseGrant.case_id == case_id,
                    CaseGrant.merchant_id == principal.merchant_id,
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if row is None:
                raise WorkflowError(404, "GRANT_NOT_FOUND")
            if row.revoked_at is None:
                session.execute(
                    update(CaseGrant)
                    .where(CaseGrant.id == row.id)
                    .values(revoked_at=func.clock_timestamp())
                )
                session.refresh(row)
            result = metadata(session, row)
            authorize_merchant(session, principal)
            return result
