"""Shared transaction-time checks. Downstream routes must also project disclosures explicitly."""

import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import func, select

from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.db.models import BrowserSession, Case, CaseGrant, EvidenceConsent, GrantEvidence
from zecsolve.schemas.access import MERCHANT_PERMISSIONS, AccessContextV1, GrantScopeV1
from zecsolve.services.workflow import WorkflowError, authorize_merchant


@dataclass(frozen=True)
class GrantPrincipal:
    merchant_id: uuid.UUID
    case_id: uuid.UUID
    grant_id: uuid.UUID
    role: Literal["customer", "reviewer"]
    session_id: uuid.UUID | None = None


def validate_session(session, principal, underlying_expiry):
    session_id = getattr(principal, "session_id", None)
    row = None
    if session_id is not None:
        row = session.scalar(
            select(BrowserSession)
            .where(BrowserSession.id == session_id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        expected = (
            principal.merchant_id,
            getattr(principal, "credential_id", None),
            getattr(principal, "grant_id", None),
            getattr(principal, "case_id", None),
        )
        if (
            row is None
            or (row.merchant_id, row.credential_id, row.grant_id, row.case_id) != expected
        ):
            raise WorkflowError(401, "INVALID_SESSION")
    now = session.scalar(select(func.clock_timestamp()))
    if underlying_expiry <= now or (
        row is not None and (row.revoked_at is not None or row.expires_at <= now)
    ):
        raise WorkflowError(401, "ACCESS_EXPIRED_OR_REVOKED")


def authorize_grant(session, principal):
    row = session.scalar(
        select(CaseGrant)
        .where(
            CaseGrant.id == principal.grant_id,
            CaseGrant.merchant_id == principal.merchant_id,
            CaseGrant.case_id == principal.case_id,
        )
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    )
    if row is None or row.role != principal.role or row.revoked_at is not None:
        raise WorkflowError(401, "INVALID_CASE_GRANT")
    validate_session(session, principal, row.expires_at)
    try:
        scope = GrantScopeV1.model_validate(row.scope)
        evidence = set(
            session.scalars(
                select(GrantEvidence.evidence_id).where(GrantEvidence.grant_id == row.id)
            )
        )
        if scope.role != row.role or evidence != set(scope.evidence_ids):
            raise ValueError("Grant scope mismatch")
    except ValueError:
        raise WorkflowError(409, "GRANT_SCOPE_UNAVAILABLE") from None
    return row, scope


def sharing_allowed(session, merchant_id, case_id, evidence_id):
    return (
        session.scalar(
            select(EvidenceConsent.id).where(
                EvidenceConsent.merchant_id == merchant_id,
                EvidenceConsent.case_id == case_id,
                EvidenceConsent.evidence_id == evidence_id,
                EvidenceConsent.processing_authorized.is_(True),
                EvidenceConsent.share_with_reviewers.is_(True),
            )
        )
        is not None
    )


def authorize_case_access(session, principal, case_id, permission, evidence_id=None):
    if isinstance(principal, MerchantPrincipal):
        authorize_merchant(session, principal)
        scope = None
        permissions = MERCHANT_PERMISSIONS
    elif isinstance(principal, GrantPrincipal):
        _, scope = authorize_grant(session, principal)
        if principal.case_id != case_id:
            raise WorkflowError(404, "CASE_NOT_FOUND")
        permissions = (
            ["case:summary", "claim:submit", "evidence:submit"]
            if scope.role == "customer"
            else ["report:read"]
        )
        if scope.evidence_ids:
            permissions.append("evidence:read")
        if scope.allow_export:
            permissions.append("case:export")
    else:
        raise WorkflowError(401, "INVALID_ACTOR")
    if (
        session.scalar(
            select(Case.id).where(Case.id == case_id, Case.merchant_id == principal.merchant_id)
        )
        is None
    ):
        raise WorkflowError(404, "CASE_NOT_FOUND")
    if permission not in permissions:
        raise WorkflowError(403, "ACTION_NOT_PERMITTED")
    if scope and permission in ("evidence:read", "case:export"):
        selected = [evidence_id] if permission == "evidence:read" else scope.evidence_ids
        for selected_id in selected:
            if selected_id not in scope.evidence_ids or not sharing_allowed(
                session, principal.merchant_id, case_id, selected_id
            ):
                raise WorkflowError(403, "EVIDENCE_NOT_PERMITTED")
    return AccessContextV1(
        role=scope.role if scope else "merchant",
        merchant_id=principal.merchant_id,
        credential_id=getattr(principal, "credential_id", None),
        grant_id=getattr(principal, "grant_id", None),
        session_id=getattr(principal, "session_id", None),
        case_id=case_id,
        permissions=permissions,
        report_sections=scope.report_sections if scope else [],
        evidence_ids=scope.evidence_ids if scope else [],
        allow_export=scope.allow_export if scope else True,
    )
