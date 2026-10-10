import hashlib
import re
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from zecsolve.db.models import Merchant, MerchantCredential

TOKEN_PATTERN = re.compile(r"zsm_[A-Za-z0-9_-]{43}\Z")


@dataclass(frozen=True)
class MerchantPrincipal:
    merchant_id: uuid.UUID
    credential_id: uuid.UUID


@dataclass(frozen=True)
class IssuedCredential:
    merchant_id: uuid.UUID
    credential_id: uuid.UUID
    expires_at: datetime
    token: str = field(repr=False)


def token_digest(token: str) -> str | None:
    if not TOKEN_PATTERN.fullmatch(token):
        return None
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def issue_credential(
    session: Session, merchant_id: uuid.UUID, ttl_days: int = 30
) -> IssuedCredential:
    """Caller owns the transaction; never disclose a token until its commit succeeds."""
    if type(ttl_days) is not int or not 1 <= ttl_days <= 365:
        raise ValueError("Credential lifetime must be 1 to 365 days")
    if session.get(Merchant, merchant_id) is None:
        raise ValueError("Merchant not found")
    token = "zsm_" + secrets.token_urlsafe(32)
    expires_at = session.scalar(select(func.clock_timestamp())) + timedelta(days=ttl_days)
    credential = MerchantCredential(
        merchant_id=merchant_id,
        token_sha256=token_digest(token),
        expires_at=expires_at,
    )
    session.add(credential)
    session.flush()
    return IssuedCredential(merchant_id, credential.id, expires_at, token)


def provision_merchant(session: Session, name: str, ttl_days: int = 30) -> IssuedCredential:
    name = name.strip()
    if not 1 <= len(name) <= 200:
        raise ValueError("Merchant name must contain 1 to 200 characters")
    merchant = Merchant(name=name)
    session.add(merchant)
    session.flush()
    return issue_credential(session, merchant.id, ttl_days)


def authenticate_merchant(session: Session, token: str) -> MerchantPrincipal | None:
    digest = token_digest(token)
    if digest is None:
        return None
    credential = session.scalar(
        select(MerchantCredential).where(
            MerchantCredential.token_sha256 == digest,
            MerchantCredential.revoked_at.is_(None),
            MerchantCredential.expires_at > func.clock_timestamp(),
        )
    )
    if credential is None:
        return None
    return MerchantPrincipal(credential.merchant_id, credential.id)


def revoke_credential(session: Session, credential_id: uuid.UUID) -> None:
    """Revocation is idempotent and does not change the first revocation timestamp."""
    if session.get(MerchantCredential, credential_id) is None:
        raise ValueError("Credential not found")
    session.execute(
        update(MerchantCredential)
        .where(MerchantCredential.id == credential_id, MerchantCredential.revoked_at.is_(None))
        .values(revoked_at=func.clock_timestamp())
    )
