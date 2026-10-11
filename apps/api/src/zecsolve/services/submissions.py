"""Submission persistence helpers consuming P1's authorization and retry foundation."""

from sqlalchemy import select

from zecsolve.auth.access import authorize_case_access
from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.db.models import AccessSubmissionRequest, Case, Claim, Invoice
from zecsolve.services.cases import load_owned_case
from zecsolve.services.workflow import WorkflowError


def actor_columns(principal):
    return {
        "credential_id": getattr(principal, "credential_id", None),
        "grant_id": getattr(principal, "grant_id", None),
    }


def actor_name(principal):
    if isinstance(principal, MerchantPrincipal):
        return f"credential:{principal.credential_id}"
    return f"grant:{principal.grant_id}"


def find_submission(session, principal, case_id, operation, key, request_hash):
    record = session.scalar(
        select(AccessSubmissionRequest).filter_by(
            merchant_id=principal.merchant_id,
            case_id=case_id,
            operation=operation,
            idempotency_key=key,
            **actor_columns(principal),
        )
    )
    if record is not None and record.request_hash != request_hash:
        raise WorkflowError(409, "IDEMPOTENCY_CONFLICT")
    return record


def lock_submission_case(session, principal, case_id, permission):
    authorize_case_access(session, principal, case_id, permission)
    current = load_owned_case(session, principal, case_id)
    invoice = session.scalar(
        select(Invoice)
        .where(Invoice.id == current.invoice_id, Invoice.merchant_id == principal.merchant_id)
        .with_for_update()
    )
    case = session.scalar(
        select(Case)
        .where(Case.id == case_id, Case.merchant_id == principal.merchant_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    authorize_case_access(session, principal, case_id, permission)
    if (
        case is None
        or invoice is None
        or case.invoice_id != invoice.id
        or case.workflow_version != "1"
    ):
        raise WorkflowError(409, "CASE_CONTEXT_UNAVAILABLE")
    return case


def validate_claim_link(session, principal, case_id, claim_id):
    if claim_id is None:
        return
    query = select(Claim).where(
        Claim.id == claim_id,
        Claim.case_id == case_id,
        Claim.merchant_id == principal.merchant_id,
    )
    # Customers may attach their own claims only; guessing another actor's ID grants no access.
    if not isinstance(principal, MerchantPrincipal):
        query = query.where(Claim.actor_grant_id == principal.grant_id)
    if session.scalar(query.with_for_update(read=True)) is None:
        raise WorkflowError(404, "CLAIM_NOT_FOUND")
