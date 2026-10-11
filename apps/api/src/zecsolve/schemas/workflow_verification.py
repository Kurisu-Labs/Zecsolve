import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, StrictBool, field_validator

from zecsolve.domain.statuses import CaseState
from zecsolve.schemas.case import CaseOpeningEventV1, CaseSummaryV1
from zecsolve.schemas.evidence import EvidenceStoredV1, EvidenceSubmittedEventV1
from zecsolve.schemas.invoice import InvoicePolicyV1, InvoiceSnapshotV1
from zecsolve.schemas.verification import Contract, HexDigest, VerificationReport, Zatoshis


class UTCRecord(Contract):
    @field_validator(
        "observed_at",
        "evaluated_at",
        "created_at",
        "generated_at",
        "at",
        "approved_at",
        check_fields=False,
    )
    @classmethod
    def utc_time(cls, value):
        return value.astimezone(UTC) if isinstance(value, datetime) else value


class CaseVerifyRequest(Contract):
    evidence_id: uuid.UUID


class OfflineObservationV1(UTCRecord):
    schema_version: Literal["1"] = "1"
    observation_id: uuid.UUID
    verification_id: uuid.UUID
    state: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    source: Literal["offline"] = "offline"
    reason_code: Literal["NO_CHAIN_OBSERVER"] = "NO_CHAIN_OBSERVER"
    observed_at: AwareDatetime
    network: Literal["mainnet"] = "mainnet"
    txid: HexDigest | None = None
    raw_tx_sha256: HexDigest | None = None
    confirmations: None = None
    block_hash: None = None
    block_height: None = None


class OwnedAllocationV1(Contract):
    output_id: str
    invoice_id: uuid.UUID
    amount_zat: Zatoshis


class OfflineEvaluationV1(Contract):
    rules_version: str
    findings: list[str]
    credited_zat: Annotated[int, Field(strict=True, ge=0)]
    outstanding_zat: Annotated[int, Field(strict=True, ge=0)]
    excess_zat: Annotated[int, Field(strict=True, ge=0)]
    candidate_zat: Zatoshis
    projected_outstanding_zat: Annotated[int, Field(strict=True, ge=0)]
    eligible_for_credit: Literal[False] = False


class EvaluationInputsV1(Contract):
    invoice: InvoiceSnapshotV1
    verification: VerificationReport
    approved_allocations: list[OwnedAllocationV1]
    foreign_conflict: StrictBool
    chain_state: Literal["UNAVAILABLE"] = "UNAVAILABLE"


class EvaluationSnapshotV1(UTCRecord):
    schema_version: Literal["1"] = "1"
    evaluation_id: uuid.UUID
    verification_id: uuid.UUID
    observation_id: uuid.UUID
    case_id: uuid.UUID
    merchant_id: uuid.UUID
    evaluated_at: AwareDatetime
    inputs: EvaluationInputsV1
    result: OfflineEvaluationV1
    snapshot_hash: HexDigest


class VerificationAttemptV1(UTCRecord):
    schema_version: Literal["1"] = "1"
    verification_id: uuid.UUID
    evidence_id: uuid.UUID
    case_id: uuid.UUID
    merchant_id: uuid.UUID
    actor_id: uuid.UUID
    created_at: AwareDatetime
    case_version: Annotated[int, Field(strict=True, ge=1)]
    case_state: CaseState
    result: VerificationReport
    observation: OfflineObservationV1
    evaluation: EvaluationSnapshotV1
    event_id: uuid.UUID


class VerificationEventV1(UTCRecord):
    schema_version: Literal["1"] = "1"
    event_id: uuid.UUID
    case_id: uuid.UUID
    sequence: Annotated[int, Field(strict=True, ge=2)]
    actor: Annotated[str, Field(pattern=r"^credential:[0-9a-f-]{36}$")]
    action: Literal["VERIFICATION_RECORDED"] = "VERIFICATION_RECORDED"
    at: AwareDatetime
    payload: dict
    payload_hash: HexDigest
    previous_hash: HexDigest
    event_hash: HexDigest

    @field_validator("payload")
    @classmethod
    def result_references_only(cls, value):
        ids = ("verification_id", "evidence_id", "observation_id", "evaluation_id")
        hashes = ("result_sha256", "evaluation_sha256")
        if set(value) != set(ids + hashes + ("case_version", "case_state")):
            raise ValueError("Invalid verification event payload")
        for key in ids:
            if not isinstance(value[key], str):
                raise ValueError("Invalid reference")
            uuid.UUID(value[key])
        for key in hashes:
            checksum = value[key]
            if (
                not isinstance(checksum, str)
                or len(checksum) != 64
                or any(c not in "0123456789abcdef" for c in checksum)
            ):
                raise ValueError("Invalid hash")
        if type(value["case_version"]) is not int or value["case_version"] < 2:
            raise ValueError("Invalid case version")
        if value["case_state"] not in ("OPEN", "AWAITING_EVIDENCE", "UNDER_REVIEW"):
            raise ValueError("Invalid case state")
        return value


class ClaimViewV1(UTCRecord):
    claim_id: uuid.UUID
    claimant_role: str
    reported_txid: str | None
    note: str | None
    created_at: AwareDatetime


class ResolutionViewV1(UTCRecord):
    resolution_id: uuid.UUID
    outcome: str
    reason: str
    approved_by: str
    approved_at: AwareDatetime


class CaseReportV1(UTCRecord):
    schema_version: Literal["1"] = "1"
    report_scope: Literal["INITIAL_OFFLINE"] = "INITIAL_OFFLINE"
    disclosure_scope: Literal["MERCHANT"] = "MERCHANT"
    generated_at: AwareDatetime
    case: CaseSummaryV1
    invoice: InvoiceSnapshotV1
    policy: InvoicePolicyV1
    claims: list[ClaimViewV1]
    evidence: list[EvidenceStoredV1]
    verifications: list[VerificationAttemptV1]
    chain_observations: list[OfflineObservationV1]
    evaluations: list[EvaluationSnapshotV1]
    selected_verification_id: uuid.UUID | None
    balances: OfflineEvaluationV1
    resolutions: list[ResolutionViewV1]
    events: list[CaseOpeningEventV1 | EvidenceSubmittedEventV1 | VerificationEventV1]
