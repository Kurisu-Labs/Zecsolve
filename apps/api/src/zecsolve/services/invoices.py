import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.db.models import Invoice, InvoiceCreationRequest, InvoicePolicy
from zecsolve.domain.snapshots import digest, invoice_snapshot
from zecsolve.schemas.address import NormalizeAddressRequest
from zecsolve.schemas.invoice import (
    InvoiceCreateRequest,
    InvoicePolicyV1,
    InvoiceSnapshotV1,
    InvoiceTermsV1,
)
from zecsolve.services.workflow import WorkflowError as InvoiceError
from zecsolve.services.workflow import authorize_merchant, transaction, validate_idempotency_key


def read_invoice_snapshot(session: Session, principal: MerchantPrincipal, invoice_id: uuid.UUID):
    row = session.scalar(
        select(Invoice).where(
            Invoice.id == invoice_id, Invoice.merchant_id == principal.merchant_id
        )
    )
    if row is None:
        raise InvoiceError(404, "INVOICE_NOT_FOUND")
    if row.policy_id is None or row.snapshot_version != "1":
        raise InvoiceError(409, "LEGACY_INVOICE_POLICY_UNAVAILABLE")
    policy = session.scalar(
        select(InvoicePolicy).where(
            InvoicePolicy.id == row.policy_id,
            InvoicePolicy.merchant_id == principal.merchant_id,
        )
    )
    return InvoiceSnapshotV1(
        invoice_id=row.id,
        merchant_id=row.merchant_id,
        policy_id=row.policy_id,
        created_at=row.created_at,
        snapshot_hash=row.snapshot_hash,
        policy=InvoicePolicyV1.model_validate(policy.config),
        terms=InvoiceTermsV1(
            expected_zat=row.expected_zat,
            network=row.network,
            pool=row.pool,
            receiver_address=row.expected_receiver,
            receiver_hex=row.receiver_hex,
            expected_memo=row.expected_memo_text,
            memo_hex=row.expected_memo.hex() if row.expected_memo is not None else None,
            expires_at=row.expires_at,
        ),
    )


class InvoiceService:
    def __init__(self, engine, normalizer, slots):
        self.engine, self.normalizer, self.slots = engine, normalizer, slots

    def transaction(self):
        return transaction(self.engine)

    def authorize(self, session: Session, principal: MerchantPrincipal):
        authorize_merchant(session, principal)

    def snapshot(self, session: Session, principal: MerchantPrincipal, invoice_id: uuid.UUID):
        return read_invoice_snapshot(session, principal, invoice_id)

    def replay(self, session, principal, key, request_hash):
        record = session.scalar(
            select(InvoiceCreationRequest).where(
                InvoiceCreationRequest.merchant_id == principal.merchant_id,
                InvoiceCreationRequest.credential_id == principal.credential_id,
                InvoiceCreationRequest.idempotency_key == key,
            )
        )
        if record is None:
            return None
        if record.request_hash != request_hash:
            raise InvoiceError(409, "IDEMPOTENCY_CONFLICT")
        return self.snapshot(session, principal, record.invoice_id)

    def get(self, principal: MerchantPrincipal, invoice_id: uuid.UUID) -> InvoiceSnapshotV1:
        with self.transaction() as session:
            self.authorize(session, principal)
            return self.snapshot(session, principal, invoice_id)

    def create(
        self, principal: MerchantPrincipal, request: InvoiceCreateRequest, key: str | None
    ) -> tuple[InvoiceSnapshotV1, bool]:
        with self.transaction() as session:
            self.authorize(session, principal)
            key = validate_idempotency_key(key)
            request_hash = digest(request.model_dump(mode="json"))
            previous = self.replay(session, principal, key, request_hash)
            if previous is not None:
                return previous, True

        # No transaction or database lock is held while Rust runs.
        if not self.slots.acquire(blocking=False):
            raise InvoiceError(429, "VERIFIER_BUSY")
        try:
            result = self.normalizer.normalize(
                NormalizeAddressRequest(
                    address=request.receiver_address,
                    network=request.network,
                    pool=request.pool,
                )
            )
        finally:
            self.slots.release()
        if result.state != "VALID":
            raise InvoiceError(
                422 if result.state in ("INVALID", "UNSUPPORTED") else 503,
                "INVALID_RECIPIENT"
                if result.state in ("INVALID", "UNSUPPORTED")
                else "NORMALIZER_UNAVAILABLE",
            )

        try:
            with self.transaction() as session:
                self.authorize(session, principal)
                previous = self.replay(session, principal, key, request_hash)
                if previous is not None:
                    return previous, True
                now = session.scalar(select(func.clock_timestamp()))
                if request.expires_at is not None and request.expires_at <= now:
                    raise InvoiceError(422, "INVOICE_ALREADY_EXPIRED")
                policy = InvoicePolicyV1()
                policy_id, invoice_id = uuid.uuid4(), uuid.uuid4()
                snapshot = invoice_snapshot(
                    invoice_id=invoice_id,
                    merchant_id=principal.merchant_id,
                    policy_id=policy_id,
                    created_at=now,
                    request=request,
                    receiver=result.receiver,
                    policy=policy,
                )
                session.add(
                    InvoicePolicy(
                        id=policy_id,
                        merchant_id=principal.merchant_id,
                        config=policy.model_dump(mode="json"),
                    )
                )
                session.flush()
                session.add(
                    Invoice(
                        id=invoice_id,
                        merchant_id=principal.merchant_id,
                        created_at=now,
                        expected_zat=request.expected_zat,
                        network=request.network,
                        pool=request.pool,
                        expected_receiver=request.receiver_address,
                        receiver_hex=result.receiver.receiver_hex,
                        expected_memo=request.memo_bytes,
                        expected_memo_text=request.expected_memo,
                        expires_at=request.expires_at,
                        policy_id=policy_id,
                        snapshot_version="1",
                        policy_version=policy.policy_version,
                        snapshot_hash=snapshot.snapshot_hash,
                    )
                )
                session.flush()
                session.add(
                    InvoiceCreationRequest(
                        merchant_id=principal.merchant_id,
                        credential_id=principal.credential_id,
                        idempotency_key=key,
                        request_hash=request_hash,
                        invoice_id=invoice_id,
                    )
                )
                session.flush()
                self.authorize(session, principal)
            return snapshot, False
        except IntegrityError as error:
            if (
                getattr(getattr(error.orig, "diag", None), "constraint_name", None)
                != "uq_invoice_creation_key"
            ):
                raise
            # A simultaneous request won; the losing invoice and policy were rolled back.
            with self.transaction() as session:
                self.authorize(session, principal)
                previous = self.replay(session, principal, key, request_hash)
                if previous is None:
                    raise InvoiceError(409, "RETRY_INVOICE_CREATION") from None
                return previous, True
