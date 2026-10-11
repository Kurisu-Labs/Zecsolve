from pydantic import ValidationError
from sqlalchemy import select

from zecsolve.db.models import CaseEvent
from zecsolve.domain.events import validate_event_chain
from zecsolve.schemas.case import CaseOpeningEventV1
from zecsolve.schemas.evidence import EvidenceSubmittedEventV1
from zecsolve.schemas.resolution import ResolutionEventV1
from zecsolve.schemas.submission import SubmissionEventV2
from zecsolve.schemas.workflow_verification import VerificationEventV1
from zecsolve.services.workflow import WorkflowError


def load_event_chain(session, case):
    events = []
    try:
        for row in session.scalars(
            select(CaseEvent).where(CaseEvent.case_id == case.id).order_by(CaseEvent.sequence)
        ):
            model = {
                "CASE_OPENED": CaseOpeningEventV1,
                "EVIDENCE_SUBMITTED": EvidenceSubmittedEventV1,
                "VERIFICATION_RECORDED": VerificationEventV1,
                "RESOLUTION_RECORDED": ResolutionEventV1,
            }.get(row.action)
            if row.schema_version == "2" and row.action in (
                "CLAIM_SUBMITTED",
                "EVIDENCE_SUBMITTED",
            ):
                model = SubmissionEventV2
            if model is None:
                raise ValueError("Unsupported audit event")
            events.append(
                model(
                    schema_version=row.schema_version,
                    event_id=row.id,
                    case_id=row.case_id,
                    sequence=row.sequence,
                    actor=row.actor,
                    action=row.action,
                    at=row.at,
                    payload=row.payload,
                    payload_hash=row.payload_hash,
                    previous_hash=row.previous_hash,
                    event_hash=row.event_hash,
                )
            )
        validate_event_chain(events, case.id, case.version)
        if events[0].payload["invoice_id"] != str(case.invoice_id):
            raise ValueError("Invoice binding mismatch")
    except (ValueError, ValidationError):
        raise WorkflowError(409, "CASE_HISTORY_UNAVAILABLE") from None
    return events
