import hashlib
import re
import secrets
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import func, select, update

from zecsolve.auth.access import GrantPrincipal, authorize_case_access
from zecsolve.auth.credentials import MerchantPrincipal, authenticate_merchant
from zecsolve.db.models import BrowserSession, CaseGrant, MerchantCredential
from zecsolve.schemas.access import MERCHANT_PERMISSIONS, AccessContextV1
from zecsolve.schemas.session import SessionInfoV1
from zecsolve.services.grants import authenticate_grant
from zecsolve.services.workflow import WorkflowError, authorize_merchant, transaction


@dataclass(frozen=True)
class IssuedSession:
    info: SessionInfoV1
    token: str = field(repr=False)
    csrf_token: str = field(repr=False)


def secret_digest(value, prefix):
    if not isinstance(value, str) or not re.fullmatch(
        re.escape(prefix) + r"_[A-Za-z0-9_-]{43}", value
    ):
        return None
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def access_context(session, principal):
    if isinstance(principal, MerchantPrincipal):
        authorize_merchant(session, principal)
        return AccessContextV1(
            role="merchant",
            merchant_id=principal.merchant_id,
            credential_id=principal.credential_id,
            session_id=principal.session_id,
            permissions=MERCHANT_PERMISSIONS,
            allow_export=True,
        )
    return authorize_case_access(
        session,
        principal,
        principal.case_id,
        "case:summary" if principal.role == "customer" else "report:read",
    )


def principal_for(session, row):
    if row.credential_id is not None:
        return MerchantPrincipal(row.merchant_id, row.credential_id, row.id)
    grant = session.get(CaseGrant, row.grant_id)
    if grant is None:
        raise WorkflowError(401, "INVALID_SESSION")
    return GrantPrincipal(row.merchant_id, row.case_id, row.grant_id, grant.role, row.id)


def session_info(row, context):
    return SessionInfoV1(
        session_id=row.id, created_at=row.created_at, expires_at=row.expires_at, access=context
    )


class SessionService:
    def __init__(self, engine):
        self.engine = engine

    def exchange(self, code):
        with transaction(self.engine) as session:
            principal = authenticate_merchant(session, code) or authenticate_grant(session, code)
            if principal is None:
                raise WorkflowError(401, "INVALID_ACCESS_CODE")
            access_context(session, principal)
            if isinstance(principal, MerchantPrincipal):
                underlying = session.get(MerchantCredential, principal.credential_id)
            else:
                underlying = session.get(CaseGrant, principal.grant_id)
            now = session.scalar(select(func.clock_timestamp()))
            expires_at = min(now + timedelta(hours=8), underlying.expires_at)
            if expires_at <= now:
                raise WorkflowError(401, "INVALID_ACCESS_CODE")
            token, csrf = "zss_" + secrets.token_urlsafe(32), "zsc_" + secrets.token_urlsafe(32)
            row = BrowserSession(
                merchant_id=principal.merchant_id,
                credential_id=getattr(principal, "credential_id", None),
                grant_id=getattr(principal, "grant_id", None),
                case_id=getattr(principal, "case_id", None),
                token_sha256=secret_digest(token, "zss"),
                csrf_sha256=secret_digest(csrf, "zsc"),
                created_at=now,
                expires_at=expires_at,
            )
            session.add(row)
            session.flush()
            context = access_context(session, principal_for(session, row))
            result = session_info(row, context)
        return IssuedSession(result, token, csrf)

    def load(self, session, token):
        hashed = secret_digest(token, "zss")
        if hashed is None:
            raise WorkflowError(401, "INVALID_SESSION")
        # Discover the parent first; lock parent before session in access_context.
        row = session.scalar(select(BrowserSession).where(BrowserSession.token_sha256 == hashed))
        if row is None:
            raise WorkflowError(401, "INVALID_SESSION")
        principal = principal_for(session, row)
        context = access_context(session, principal)
        return principal, session_info(row, context), row.csrf_sha256

    def authenticate(self, token):
        with transaction(self.engine) as session:
            return self.load(session, token)

    def logout(self, token):
        with transaction(self.engine) as session:
            principal, info, _ = self.load(session, token)
            session.execute(
                update(BrowserSession)
                .where(BrowserSession.id == info.session_id, BrowserSession.revoked_at.is_(None))
                .values(revoked_at=func.clock_timestamp())
            )
            # Parent remains locked through commit; this session is deliberately revoked.
