import uuid
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, StrictBool, field_validator, model_validator

from zecsolve.domain.statuses import CaseState, ChainState
from zecsolve.schemas.case import CaseOpeningEventV1
from zecsolve.schemas.evidence import EvidenceSubmittedEventV1
from zecsolve.schemas.invoice import InvoiceSnapshotV1
from zecsolve.schemas.verification import Contract, HexDigest, VerificationReport, Zatoshis
from zecsolve.schemas.workflow_verification import (
    CaseReportV1,
    OfflineEvaluationV1,
    OwnedAllocationV1,
    UTCRecord,
    VerificationEventV1,
)

Action = Literal["APPROVE_OUTPUT", "REQUEST_EVIDENCE", "REJECT_EVIDENCE", "CLOSE_UNRESOLVED"]


class ResolveRequest(Contract):
    action: Action
    verification_id: uuid.UUID | None = None
    expected_case_version: Annotated[int, Field(strict=True, ge=1)]
    reason: str

    @field_validator("reason")
    @classmethod
    def bounded_reason(cls, value):
        if not value.strip() or "\0" in value or len(value.encode("utf-8")) > 2000:
            raise ValueError("A nonempty reason up to 2000 UTF-8 bytes is required")
        return value

    @model_validator(mode="after")
    def evidence_reference(self):
        if (self.action in ("APPROVE_OUTPUT", "REJECT_EVIDENCE")) != (
            self.verification_id is not None
        ):
            raise ValueError("Only approval and rejection require a verification reference")
        return self


class DecisionObservationV1(UTCRecord):
    schema_version: Literal["decision-observation-v1"] = "decision-observation-v1"
    observation_id: uuid.UUID
    verification_id: uuid.UUID
    state: ChainState
    source_kind: Literal["OFFLINE", "RPC", "SIMULATED"]
    source: Annotated[str, Field(min_length=1, max_length=200)]
    reason_code: Annotated[str, Field(pattern=r"^[A-Z0-9_]{1,80}$")]
    observed_at: AwareDatetime
    network: Literal["mainnet"] = "mainnet"
    txid: HexDigest | None = None
    raw_tx_sha256: HexDigest | None = None
    confirmations: Annotated[int, Field(strict=True, ge=0, le=2147483647)] | None = None
    block_hash: HexDigest | None = None
    block_height: Annotated[int, Field(strict=True, ge=0)] | None = None

    @model_validator(mode="after")
    def confirmed_context(self):
        if self.state == "CONFIRMED" and any(
            value is None
            for value in (
                self.txid,
                self.raw_tx_sha256,
                self.confirmations,
                self.block_hash,
                self.block_height,
            )
        ):
            raise ValueError("Confirmed observations require full transaction and block context")
        return self


class DecisionEvaluationV1(OfflineEvaluationV1):
    eligible_for_credit: StrictBool


class DecisionSnapshotV1(UTCRecord):
    schema_version: Literal["decision-evaluation-v1"] = "decision-evaluation-v1"
    evaluation_id: uuid.UUID
    case_id: uuid.UUID
    merchant_id: uuid.UUID
    evaluated_at: AwareDatetime
    invoice: InvoiceSnapshotV1
    verification_id: uuid.UUID | None
    verification: VerificationReport | None
    observation: DecisionObservationV1 | None
    source_authorized: StrictBool
    approved_allocations: list[OwnedAllocationV1]
    foreign_conflict: StrictBool
    result: DecisionEvaluationV1
    snapshot_hash: HexDigest


class ResolutionOutcomeV1(UTCRecord):
    schema_version: Literal["1"] = "1"
    resolution_id: uuid.UUID
    case_id: uuid.UUID
    merchant_id: uuid.UUID
    invoice_id: uuid.UUID
    actor_id: uuid.UUID
    action: Action
    reason: str
    decided_at: AwareDatetime
    verification_id: uuid.UUID | None
    output_id: str | None
    allocated_zat: Zatoshis
    case_version: Annotated[int, Field(strict=True, ge=2)]
    case_state: CaseState
    evaluation: DecisionSnapshotV1
    balances: OfflineEvaluationV1
    event_id: uuid.UUID


class ResolutionEventV1(UTCRecord):
    schema_version: Literal["1"] = "1"
    event_id: uuid.UUID
    case_id: uuid.UUID
    sequence: Annotated[int, Field(strict=True, ge=2)]
    actor: Annotated[str, Field(pattern=r"^credential:[0-9a-f-]{36}$")]
    action: Literal["RESOLUTION_RECORDED"] = "RESOLUTION_RECORDED"
    at: AwareDatetime
    payload: dict
    payload_hash: HexDigest
    previous_hash: HexDigest
    event_hash: HexDigest

    @field_validator("payload")
    @classmethod
    def safe_references(cls, value):
        class References(Contract):
            resolution_id: uuid.UUID
            evaluation_id: uuid.UUID
            outcome_sha256: HexDigest
            case_version: Annotated[int, Field(strict=True, ge=2)]
            case_state: CaseState

        checked = References.model_validate(value).model_dump(mode="json")
        if checked != value:
            raise ValueError("Noncanonical resolution references")
        return value


class MerchantCaseReportV1(CaseReportV1):
    report_scope: Literal["INITIAL_OFFLINE", "MERCHANT_DECISIONS", "SIMULATED_DECISIONS"] = (
        "INITIAL_OFFLINE"
    )
    decision_observations: list[DecisionObservationV1] = Field(default_factory=list)
    decision_evaluations: list[DecisionSnapshotV1] = Field(default_factory=list)
    decisions: list[ResolutionOutcomeV1] = Field(default_factory=list)
    events: list[
        CaseOpeningEventV1 | EvidenceSubmittedEventV1 | VerificationEventV1 | ResolutionEventV1
    ]
