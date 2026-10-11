"""Foundation schema. Case services and merchant authorization arrive in the next milestone."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Identified:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Merchant(Identified, Timestamped, Base):
    __tablename__ = "merchants"
    name: Mapped[str] = mapped_column(String(200))


class MerchantCredential(Identified, Timestamped, Base):
    __tablename__ = "merchant_credentials"
    __table_args__ = (
        UniqueConstraint("id", "merchant_id", name="uq_credential_merchant"),
        UniqueConstraint("token_sha256", name="uq_merchant_credential_token"),
        CheckConstraint("token_sha256 ~ '^[0-9a-f]{64}$'", name="ck_credential_digest"),
        CheckConstraint("expires_at > created_at", name="ck_credential_expiry"),
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    token_sha256: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InvoicePolicy(Identified, Timestamped, Base):
    __tablename__ = "invoice_policies"
    __table_args__ = (UniqueConstraint("id", "merchant_id", name="uq_policy_merchant"),)
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id"))
    config: Mapped[dict] = mapped_column(JSON)


class Invoice(Identified, Timestamped, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        ForeignKeyConstraint(
            ["policy_id", "merchant_id"],
            ["invoice_policies.id", "invoice_policies.merchant_id"],
            name="fk_invoice_policy_merchant",
        ),
        UniqueConstraint("id", "merchant_id", name="uq_invoice_merchant"),
        CheckConstraint(
            "expected_zat > 0 AND expected_zat <= 2100000000000000", name="ck_invoice_amount"
        ),
        CheckConstraint("network IN ('mainnet', 'testnet', 'regtest')", name="ck_invoice_network"),
        CheckConstraint("pool IN ('orchard', 'sapling')", name="ck_invoice_pool"),
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id"))
    network: Mapped[str] = mapped_column(String(16))
    pool: Mapped[str] = mapped_column(String(16))
    expected_zat: Mapped[int] = mapped_column(BigInteger)
    expected_receiver: Mapped[str] = mapped_column(Text)
    receiver_hex: Mapped[str] = mapped_column(String(86))
    expected_memo: Mapped[bytes | None] = mapped_column(LargeBinary)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    policy_version: Mapped[str] = mapped_column(String(40))
    # Null only for historical snapshots; never infer a policy for those rows.
    policy_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    snapshot_version: Mapped[str | None] = mapped_column(String(16))
    expected_memo_text: Mapped[str | None] = mapped_column(Text)


class InvoiceCreationRequest(Identified, Timestamped, Base):
    __tablename__ = "invoice_creation_requests"
    __table_args__ = (
        UniqueConstraint(
            "merchant_id", "credential_id", "idempotency_key", name="uq_invoice_creation_key"
        ),
        ForeignKeyConstraint(
            ["credential_id", "merchant_id"],
            ["merchant_credentials.id", "merchant_credentials.merchant_id"],
            name="fk_invoice_request_credential",
        ),
        ForeignKeyConstraint(
            ["invoice_id", "merchant_id"],
            ["invoices.id", "invoices.merchant_id"],
            name="fk_invoice_request_owner",
        ),
        CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'", name="ck_invoice_request_hash"),
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    credential_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    invoice_id: Mapped[uuid.UUID] = mapped_column(Uuid)


class Case(Identified, Timestamped, Base):
    __tablename__ = "cases"
    __table_args__ = (
        ForeignKeyConstraint(
            ["invoice_id", "merchant_id"], ["invoices.id", "invoices.merchant_id"]
        ),
        CheckConstraint(
            "state IN ('OPEN','AWAITING_EVIDENCE','UNDER_REVIEW','RESOLVED','CLOSED_UNRESOLVED')",
            name="ck_case_state",
        ),
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    category: Mapped[str | None] = mapped_column(String(40))
    state: Mapped[str] = mapped_column(String(32), default="OPEN")
    version: Mapped[int] = mapped_column(Integer, default=1)


class Claim(Identified, Timestamped, Base):
    __tablename__ = "claims"
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    claimant_role: Mapped[str] = mapped_column(String(32))
    reported_txid: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text)


class Evidence(Identified, Timestamped, Base):
    __tablename__ = "evidence"
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    type: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(200))
    sha256: Mapped[str] = mapped_column(String(64))
    storage_ref: Mapped[str] = mapped_column(Text)


class Verification(Identified, Timestamped, Base):
    __tablename__ = "verifications"
    __table_args__ = (
        CheckConstraint(
            "receipt_state IN ('NONE','VALID','INVALID','UNSUPPORTED','UNAVAILABLE','ERROR')",
            name="ck_verification_state",
        ),
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id"), index=True)
    receipt_state: Mapped[str] = mapped_column(String(16))
    # Complete, versioned result including input hashes and recovered fields.
    result: Mapped[dict] = mapped_column(JSON)
    verifier_version: Mapped[str] = mapped_column(String(120))
    rules_version: Mapped[str] = mapped_column(String(40))


class ChainObservation(Identified, Timestamped, Base):
    __tablename__ = "chain_observations"
    __table_args__ = (
        CheckConstraint(
            "state IN ('CONFIRMED','UNCONFIRMED','UNAVAILABLE')", name="ck_chain_state"
        ),
    )
    verification_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("verifications.id"), index=True)
    state: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    block_hash: Mapped[str | None] = mapped_column(String(64))
    block_height: Mapped[int | None] = mapped_column(BigInteger)
    confirmations: Mapped[int | None] = mapped_column(Integer)


class Resolution(Identified, Base):
    __tablename__ = "resolutions"
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    outcome: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(Text)
    approved_by: Mapped[str] = mapped_column(String(200))
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OutputAllocation(Timestamped, Base):
    __tablename__ = "output_allocations"
    __table_args__ = (
        CheckConstraint(
            "amount_zat >= 0 AND amount_zat <= 2100000000000000", name="ck_allocation_amount"
        ),
        CheckConstraint("output_index >= 0 AND output_index <= 4294967295", name="ck_output_index"),
        CheckConstraint(
            "network IN ('mainnet', 'testnet', 'regtest')", name="ck_allocation_network"
        ),
        CheckConstraint("pool IN ('orchard', 'sapling')", name="ck_allocation_pool"),
        CheckConstraint("txid ~ '^[0-9a-f]{64}$'", name="ck_allocation_txid"),
    )
    network: Mapped[str] = mapped_column(String(16), primary_key=True)
    pool: Mapped[str] = mapped_column(String(16), primary_key=True)
    txid: Mapped[str] = mapped_column(String(64), primary_key=True)
    output_index: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), index=True)
    verification_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("verifications.id"))
    resolution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resolutions.id"))
    amount_zat: Mapped[int] = mapped_column(BigInteger)


class CaseEvent(Identified, Base):
    __tablename__ = "case_events"
    __table_args__ = (UniqueConstraint("case_id", "sequence", name="uq_case_event_sequence"),)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(80))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    payload_hash: Mapped[str] = mapped_column(String(64))
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64))
