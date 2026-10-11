"""Merchant workflow snapshots, encrypted evidence, and audit records."""

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
        UniqueConstraint("invoice_id", name="uq_case_invoice"),
        UniqueConstraint("id", "merchant_id", name="uq_case_merchant"),
        CheckConstraint("version >= 1", name="ck_case_version"),
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
    workflow_version: Mapped[str | None] = mapped_column(String(16))


class CaseCreationRequest(Identified, Timestamped, Base):
    __tablename__ = "case_creation_requests"
    __table_args__ = (
        UniqueConstraint(
            "merchant_id", "credential_id", "idempotency_key", name="uq_case_creation_key"
        ),
        ForeignKeyConstraint(
            ["credential_id", "merchant_id"],
            ["merchant_credentials.id", "merchant_credentials.merchant_id"],
            name="fk_case_request_credential",
        ),
        ForeignKeyConstraint(
            ["case_id", "merchant_id"],
            ["cases.id", "cases.merchant_id"],
            name="fk_case_request_owner",
        ),
        CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'", name="ck_case_request_hash"),
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    credential_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid)


class Claim(Identified, Timestamped, Base):
    __tablename__ = "claims"
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    claimant_role: Mapped[str] = mapped_column(String(32))
    reported_txid: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text)


class Evidence(Identified, Timestamped, Base):
    __tablename__ = "evidence"
    __table_args__ = (
        UniqueConstraint("id", "case_id", "merchant_id", name="uq_evidence_case_owner"),
        ForeignKeyConstraint(
            ["case_id", "merchant_id"],
            ["cases.id", "cases.merchant_id"],
            name="fk_evidence_case_owner",
        ),
        ForeignKeyConstraint(
            ["submitted_by", "merchant_id"],
            ["merchant_credentials.id", "merchant_credentials.merchant_id"],
            name="fk_evidence_submitter",
        ),
    )
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    type: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(200))
    sha256: Mapped[str] = mapped_column(String(64))
    storage_ref: Mapped[str] = mapped_column(Text)
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    bundle_version: Mapped[str | None] = mapped_column(String(16))
    bundle_metadata: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))


class EvidenceContent(Base):
    __tablename__ = "evidence_contents"
    __table_args__ = (
        UniqueConstraint("key_id", "nonce", name="uq_evidence_key_nonce"),
        CheckConstraint("octet_length(nonce) = 12", name="ck_evidence_nonce_length"),
        CheckConstraint(
            "octet_length(ciphertext) BETWEEN 16 AND 4200016", name="ck_evidence_ciphertext_size"
        ),
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id"), primary_key=True)
    key_id: Mapped[str] = mapped_column(String(64))
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)


class EvidenceSubmissionRequest(Identified, Timestamped, Base):
    __tablename__ = "evidence_submission_requests"
    __table_args__ = (
        UniqueConstraint(
            "merchant_id",
            "credential_id",
            "case_id",
            "idempotency_key",
            name="uq_evidence_submission_key",
        ),
        ForeignKeyConstraint(
            ["credential_id", "merchant_id"],
            ["merchant_credentials.id", "merchant_credentials.merchant_id"],
            name="fk_evidence_request_credential",
        ),
        ForeignKeyConstraint(
            ["evidence_id", "case_id", "merchant_id"],
            ["evidence.id", "evidence.case_id", "evidence.merchant_id"],
            name="fk_evidence_request_owner",
        ),
        ForeignKeyConstraint(
            ["event_id", "case_id"],
            ["case_events.id", "case_events.case_id"],
            name="fk_evidence_request_event",
        ),
        CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'", name="ck_evidence_request_hash"),
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    credential_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    evidence_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid)


class Verification(Identified, Timestamped, Base):
    __tablename__ = "verifications"
    __table_args__ = (
        UniqueConstraint("id", "case_id", "merchant_id", name="uq_verification_case_owner"),
        ForeignKeyConstraint(
            ["evidence_id", "case_id", "merchant_id"],
            ["evidence.id", "evidence.case_id", "evidence.merchant_id"],
            name="fk_verification_evidence_owner",
        ),
        ForeignKeyConstraint(
            ["actor_id", "merchant_id"],
            ["merchant_credentials.id", "merchant_credentials.merchant_id"],
            name="fk_verification_actor",
        ),
        ForeignKeyConstraint(
            ["event_id", "case_id"],
            ["case_events.id", "case_events.case_id"],
            name="fk_verification_event",
            deferrable=True,
            initially="DEFERRED",
        ),
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
    case_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    workflow_version: Mapped[str | None] = mapped_column(String(16))
    case_version: Mapped[int | None] = mapped_column(Integer)
    case_state: Mapped[str | None] = mapped_column(String(32))


class ChainObservation(Identified, Timestamped, Base):
    __tablename__ = "chain_observations"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "verification_id",
            "case_id",
            "merchant_id",
            name="uq_observation_verification_owner",
        ),
        ForeignKeyConstraint(
            ["verification_id", "case_id", "merchant_id"],
            ["verifications.id", "verifications.case_id", "verifications.merchant_id"],
            name="fk_observation_verification_owner",
        ),
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
    case_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    provenance: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))


class VerificationEvaluation(Identified, Timestamped, Base):
    __tablename__ = "verification_evaluations"
    __table_args__ = (
        UniqueConstraint("verification_id", name="uq_evaluation_verification"),
        ForeignKeyConstraint(
            ["verification_id", "case_id", "merchant_id"],
            ["verifications.id", "verifications.case_id", "verifications.merchant_id"],
            name="fk_evaluation_verification_owner",
        ),
        ForeignKeyConstraint(
            ["observation_id", "verification_id", "case_id", "merchant_id"],
            [
                "chain_observations.id",
                "chain_observations.verification_id",
                "chain_observations.case_id",
                "chain_observations.merchant_id",
            ],
            name="fk_evaluation_observation",
        ),
        ForeignKeyConstraint(
            ["invoice_id", "merchant_id"],
            ["invoices.id", "invoices.merchant_id"],
            name="fk_evaluation_invoice",
        ),
        ForeignKeyConstraint(
            ["policy_id", "merchant_id"],
            ["invoice_policies.id", "invoice_policies.merchant_id"],
            name="fk_evaluation_policy",
        ),
    )
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    invoice_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    policy_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    verification_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    observation_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    snapshot: Mapped[dict] = mapped_column(JSON)


class CaseVerificationRequest(Identified, Timestamped, Base):
    __tablename__ = "case_verification_requests"
    __table_args__ = (
        UniqueConstraint(
            "merchant_id",
            "credential_id",
            "case_id",
            "idempotency_key",
            name="uq_case_verification_key",
        ),
        ForeignKeyConstraint(
            ["credential_id", "merchant_id"],
            ["merchant_credentials.id", "merchant_credentials.merchant_id"],
            name="fk_verify_request_credential",
        ),
        ForeignKeyConstraint(
            ["verification_id", "case_id", "merchant_id"],
            ["verifications.id", "verifications.case_id", "verifications.merchant_id"],
            name="fk_verify_request_owner",
        ),
        CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'", name="ck_verify_request_hash"),
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    credential_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    verification_id: Mapped[uuid.UUID] = mapped_column(Uuid)


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
    __table_args__ = (
        UniqueConstraint("case_id", "sequence", name="uq_case_event_sequence"),
        UniqueConstraint("id", "case_id", name="uq_event_case"),
    )
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(80))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    payload_hash: Mapped[str] = mapped_column(String(64))
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64))
    # Legacy event hashes remain unchanged; their original payload is unknown.
    schema_version: Mapped[str | None] = mapped_column(String(16))
    payload: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
