import uuid

from sqlalchemy import func, select

from zecsolve.auth.access import authorize_case_access
from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.db.models import AccessSubmissionRequest, CaseEvent, Claim
from zecsolve.domain.events import scoped_submission_event
from zecsolve.domain.snapshots import digest
from zecsolve.schemas.submission import ClaimSubmitRequest, SubmissionAcknowledgementV1
from zecsolve.services.audit import load_event_chain
from zecsolve.services.submissions import (
    actor_columns,
    actor_name,
    find_submission,
    lock_submission_case,
)
from zecsolve.services.workflow import WorkflowError, transaction, validate_idempotency_key


def validate_claim_record(claim, events):
    """Preserve legacy claims; bind attributed claims to their recorded request and consent."""
    if claim.actor_credential_id is None and claim.actor_grant_id is None:
        return
    matching = [
        event
        for event in events
        if event.action == "CLAIM_SUBMITTED" and event.payload.get("claim_id") == str(claim.id)
    ]
    try:
        if len(matching) != 1:
            raise ValueError("Missing claim event")
        event = matching[0]
        request = ClaimSubmitRequest(
            note=claim.note,
            reported_txid=claim.reported_txid,
            **{
                name: event.payload[name]
                for name in (
                    "disclosure_version",
                    "processing_authorized",
                    "share_with_reviewers",
                )
            },
        )
        merchant = claim.actor_credential_id is not None
        actor = (
            f"credential:{claim.actor_credential_id}"
            if merchant
            else f"grant:{claim.actor_grant_id}"
        )
        if (
            event.case_id != claim.case_id
            or event.actor != actor
            or event.at != claim.created_at
            or claim.claimant_role != ("merchant" if merchant else "customer")
            or event.payload["request_sha256"] != digest(request.model_dump(mode="json"))
        ):
            raise ValueError("Claim history mismatch")
    except (ValueError, KeyError):
        raise WorkflowError(409, "CLAIM_CONTEXT_UNAVAILABLE") from None


class ClaimService:
    def __init__(self, engine):
        self.engine = engine

    def submit(self, principal, case_id, request, key):
        with transaction(self.engine) as session:
            authorize_case_access(session, principal, case_id, "claim:submit")
            key = validate_idempotency_key(key)
            request_hash = digest(request.model_dump(mode="json"))
            # Serialize retries with every other case writer, using the shared lock order.
            case = lock_submission_case(session, principal, case_id, "claim:submit")
            events = load_event_chain(session, case)
            previous = find_submission(session, principal, case_id, "claim", key, request_hash)
            if previous is not None:
                claim = session.get(Claim, previous.claim_id)
                event = next((item for item in events if item.event_id == previous.event_id), None)
                if (
                    claim is None
                    or event is None
                    or event.action != "CLAIM_SUBMITTED"
                    or event.actor != actor_name(principal)
                    or event.payload.get("claim_id") != str(claim.id)
                    or event.payload.get("request_sha256") != request_hash
                    or (
                        claim.case_id,
                        claim.merchant_id,
                        claim.actor_credential_id,
                        claim.actor_grant_id,
                    )
                    != (
                        case_id,
                        principal.merchant_id,
                        actor_columns(principal)["credential_id"],
                        actor_columns(principal)["grant_id"],
                    )
                    or (claim.note, claim.reported_txid) != (request.note, request.reported_txid)
                ):
                    raise WorkflowError(409, "CLAIM_CONTEXT_UNAVAILABLE")
                authorize_case_access(session, principal, case_id, "claim:submit")
                return SubmissionAcknowledgementV1(
                    operation="claim", submission_id=claim.id, accepted_at=claim.created_at
                ), True
            if case.state in ("RESOLVED", "CLOSED_UNRESOLVED"):
                raise WorkflowError(409, "CASE_TERMINAL")
            now = session.scalar(select(func.clock_timestamp()))
            claim = Claim(
                id=uuid.uuid4(),
                case_id=case_id,
                merchant_id=principal.merchant_id,
                actor_credential_id=getattr(principal, "credential_id", None),
                actor_grant_id=getattr(principal, "grant_id", None),
                claimant_role="merchant"
                if isinstance(principal, MerchantPrincipal)
                else "customer",
                reported_txid=request.reported_txid,
                note=request.note,
                created_at=now,
            )
            case.version += 1
            event = scoped_submission_event(
                event_id=uuid.uuid4(),
                case_id=case_id,
                actor=actor_name(principal),
                action="CLAIM_SUBMITTED",
                sequence=case.version,
                at=now,
                previous_hash=events[-1].event_hash,
                payload={
                    "claim_id": str(claim.id),
                    "request_sha256": request_hash,
                    "disclosure_version": request.disclosure_version,
                    "processing_authorized": request.processing_authorized,
                    "share_with_reviewers": request.share_with_reviewers,
                    "case_version": case.version,
                    "case_state": case.state,
                },
            )
            session.add(claim)
            session.add(CaseEvent(id=event.event_id, **event.model_dump(exclude={"event_id"})))
            session.flush()
            session.add(
                AccessSubmissionRequest(
                    merchant_id=principal.merchant_id,
                    case_id=case_id,
                    **actor_columns(principal),
                    operation="claim",
                    claim_id=claim.id,
                    event_id=event.event_id,
                    idempotency_key=key,
                    request_hash=request_hash,
                )
            )
            session.flush()
            authorize_case_access(session, principal, case_id, "claim:submit")
            result = SubmissionAcknowledgementV1(
                operation="claim", submission_id=claim.id, accepted_at=now
            )
        return result, False
