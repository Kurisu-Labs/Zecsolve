import uuid

from pydantic import ValidationError
from sqlalchemy import func, select, tuple_
from sqlalchemy.exc import IntegrityError

from zecsolve.db.models import Case, CaseCreationRequest, CaseEvent, Invoice
from zecsolve.domain.events import opening_event
from zecsolve.domain.snapshots import digest
from zecsolve.schemas.case import (
    CaseCreateRequest,
    CaseDetailV1,
    CaseListQuery,
    CaseListV1,
    CaseOpenedV1,
    CaseOpeningEventV1,
    CaseSummaryV1,
)
from zecsolve.services.case_cursor import decode_case_cursor, encode_case_cursor
from zecsolve.services.workflow import (
    WorkflowError,
    authorize_merchant,
    transaction,
    validate_idempotency_key,
)


def load_owned_case(session, principal, case_id):
    case = session.scalar(
        select(Case).where(Case.id == case_id, Case.merchant_id == principal.merchant_id)
    )
    if case is None:
        raise WorkflowError(404, "CASE_NOT_FOUND")
    if case.workflow_version != "1":
        raise WorkflowError(409, "LEGACY_CASE_HISTORY_UNAVAILABLE")
    return case


class CaseService:
    def __init__(self, engine):
        self.engine = engine

    def list(self, principal, query: CaseListQuery) -> CaseListV1:
        with transaction(self.engine) as session:
            authorize_merchant(session, principal)
            statement = select(
                Case.id.label("case_id"),
                Case.invoice_id,
                Case.merchant_id,
                Case.state,
                Case.version,
                Case.created_at,
            ).where(Case.merchant_id == principal.merchant_id)
            if query.state is not None:
                statement = statement.where(Case.state == query.state.value)
            if query.cursor is not None:
                anchor_id = decode_case_cursor(query.cursor, principal.merchant_id, query.state)
                # A cursor is a position, not authority. Look up its ordering key only
                # within the authenticated merchant, even if the token was forged.
                anchor = session.execute(
                    select(Case.created_at, Case.id).where(
                        Case.id == anchor_id, Case.merchant_id == principal.merchant_id
                    )
                ).one_or_none()
                if anchor is None:
                    raise WorkflowError(422, "INVALID_CASE_CURSOR")
                statement = statement.where(
                    tuple_(Case.created_at, Case.id) < tuple_(anchor.created_at, anchor.id)
                )
            rows = (
                session.execute(
                    statement.order_by(Case.created_at.desc(), Case.id.desc()).limit(
                        query.limit + 1
                    )
                )
                .mappings()
                .all()
            )
            items = [CaseSummaryV1(**row) for row in rows[: query.limit]]
            next_cursor = None
            if len(rows) > query.limit:
                next_cursor = encode_case_cursor(
                    principal.merchant_id, items[-1].case_id, query.state
                )
            result = CaseListV1(items=items, next_cursor=next_cursor)
            authorize_merchant(session, principal)
            return result

    def load(self, session, principal, case_id):
        return load_owned_case(session, principal, case_id)

    def initial_event(self, session, case) -> CaseOpeningEventV1:
        row = session.scalar(
            select(CaseEvent).where(CaseEvent.case_id == case.id, CaseEvent.sequence == 1)
        )
        if row is None or row.schema_version != "1" or row.payload is None:
            raise WorkflowError(409, "CASE_HISTORY_UNAVAILABLE")
        try:
            event = CaseOpeningEventV1(
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
        except ValidationError:
            raise WorkflowError(409, "CASE_HISTORY_UNAVAILABLE") from None
        header = event.model_dump(mode="json", exclude={"event_id", "payload", "event_hash"})
        if (
            event.payload_hash != digest(event.payload)
            or event.event_hash != digest(header)
            or event.payload.get("invoice_id") != str(case.invoice_id)
        ):
            raise WorkflowError(409, "CASE_HISTORY_UNAVAILABLE")
        return event

    def opened(self, session, case) -> CaseOpenedV1:
        return CaseOpenedV1(
            case_id=case.id,
            invoice_id=case.invoice_id,
            merchant_id=case.merchant_id,
            created_at=case.created_at,
            opening_event=self.initial_event(session, case),
        )

    def replay(self, session, principal, key, request_hash):
        record = session.scalar(
            select(CaseCreationRequest).where(
                CaseCreationRequest.merchant_id == principal.merchant_id,
                CaseCreationRequest.credential_id == principal.credential_id,
                CaseCreationRequest.idempotency_key == key,
            )
        )
        if record is None:
            return None
        if record.request_hash != request_hash:
            raise WorkflowError(409, "IDEMPOTENCY_CONFLICT")
        return self.opened(session, self.load(session, principal, record.case_id))

    def get(self, principal, case_id: uuid.UUID) -> CaseDetailV1:
        with transaction(self.engine) as session:
            authorize_merchant(session, principal)
            case = self.load(session, principal, case_id)
            result = CaseDetailV1(
                case_id=case.id,
                invoice_id=case.invoice_id,
                merchant_id=case.merchant_id,
                state=case.state,
                version=case.version,
                created_at=case.created_at,
                opening_event=self.initial_event(session, case),
            )
            authorize_merchant(session, principal)
            return result

    def create(
        self, principal, request: CaseCreateRequest, key: str | None
    ) -> tuple[CaseOpenedV1, bool]:
        try:
            with transaction(self.engine) as session:
                authorize_merchant(session, principal)
                key = validate_idempotency_key(key)
                request_hash = digest(request.model_dump(mode="json"))
                previous = self.replay(session, principal, key, request_hash)
                if previous is not None:
                    authorize_merchant(session, principal)
                    return previous, True
                # Serialize invoice-affecting writes in invoice -> case order.
                invoice = session.scalar(
                    select(Invoice)
                    .where(
                        Invoice.id == request.invoice_id,
                        Invoice.merchant_id == principal.merchant_id,
                    )
                    .with_for_update()
                )
                if invoice is None:
                    raise WorkflowError(404, "INVOICE_NOT_FOUND")
                authorize_merchant(session, principal)
                if (
                    invoice.policy_id is None
                    or invoice.snapshot_version != "1"
                    or invoice.policy_version != "invoice-policy-v1"
                ):
                    raise WorkflowError(409, "LEGACY_INVOICE_POLICY_UNAVAILABLE")
                previous = self.replay(session, principal, key, request_hash)
                if previous is not None:
                    return previous, True
                case = session.scalar(
                    select(Case)
                    .where(
                        Case.invoice_id == invoice.id,
                        Case.merchant_id == principal.merchant_id,
                    )
                    .with_for_update()
                )
                authorize_merchant(session, principal)
                replayed = case is not None
                if case is None:
                    now = session.scalar(select(func.clock_timestamp()))
                    case = Case(
                        id=uuid.uuid4(),
                        invoice_id=invoice.id,
                        merchant_id=principal.merchant_id,
                        state="OPEN",
                        version=1,
                        workflow_version="1",
                        created_at=now,
                    )
                    session.add(case)
                    session.flush()
                    event = opening_event(
                        event_id=uuid.uuid4(),
                        case_id=case.id,
                        credential_id=principal.credential_id,
                        invoice_id=invoice.id,
                        invoice_snapshot_hash=invoice.snapshot_hash,
                        policy_id=invoice.policy_id,
                        at=now,
                    )
                    session.add(
                        CaseEvent(
                            id=event.event_id,
                            case_id=event.case_id,
                            sequence=event.sequence,
                            actor=event.actor,
                            action=event.action,
                            at=event.at,
                            payload=event.payload,
                            payload_hash=event.payload_hash,
                            previous_hash=event.previous_hash,
                            event_hash=event.event_hash,
                            schema_version=event.schema_version,
                        )
                    )
                    session.flush()
                if case.workflow_version != "1":
                    raise WorkflowError(409, "LEGACY_CASE_HISTORY_UNAVAILABLE")
                result = self.opened(session, case)
                session.add(
                    CaseCreationRequest(
                        merchant_id=principal.merchant_id,
                        credential_id=principal.credential_id,
                        idempotency_key=key,
                        request_hash=request_hash,
                        case_id=case.id,
                    )
                )
                session.flush()
                authorize_merchant(session, principal)
            return result, replayed
        except IntegrityError as error:
            if (
                getattr(getattr(error.orig, "diag", None), "constraint_name", None)
                != "uq_case_creation_key"
            ):
                raise
            with transaction(self.engine) as session:
                authorize_merchant(session, principal)
                previous = self.replay(session, principal, key, request_hash)
                if previous is None:
                    raise WorkflowError(409, "RETRY_CASE_CREATION") from None
                authorize_merchant(session, principal)
                return previous, True
