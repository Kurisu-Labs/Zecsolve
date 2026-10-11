import re
from contextlib import contextmanager

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.db.models import MerchantCredential


class WorkflowError(Exception):
    def __init__(self, status: int, code: str, details: dict | None = None):
        super().__init__(code)
        self.status, self.code = status, code
        self.details = details


@contextmanager
def transaction(engine):
    with Session(engine) as session, session.begin():
        session.execute(text("SET LOCAL lock_timeout = '5s'"))
        yield session


def authorize_merchant(session: Session, principal: MerchantPrincipal):
    if not isinstance(principal, MerchantPrincipal):
        raise WorkflowError(403, "MERCHANT_REQUIRED")
    credential = session.scalar(
        select(MerchantCredential)
        .where(
            MerchantCredential.id == principal.credential_id,
            MerchantCredential.merchant_id == principal.merchant_id,
        )
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    )
    # Evaluate time after acquiring the lock: a lock-only wait can outlive expiry.
    now = session.scalar(select(func.clock_timestamp()))
    if credential is None or credential.revoked_at is not None or credential.expires_at <= now:
        raise WorkflowError(401, "INVALID_MERCHANT_CREDENTIALS")

    if principal.session_id is not None:
        from zecsolve.auth.access import validate_session

        validate_session(session, principal, credential.expires_at)


def validate_idempotency_key(key: str | None) -> str:
    if key is None or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", key):
        raise WorkflowError(422, "INVALID_IDEMPOTENCY_KEY")
    return key
