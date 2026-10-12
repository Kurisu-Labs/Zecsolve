"""Explicit reviewer projections; nested merchant snapshots never cross this boundary."""

import uuid
from typing import Literal

from pydantic import AwareDatetime, Field

from zecsolve.domain.statuses import CaseState
from zecsolve.schemas.access import ReportSection
from zecsolve.schemas.invoice import InvoicePolicyV1, InvoiceTermsV1
from zecsolve.schemas.resolution import DecisionObservationV1
from zecsolve.schemas.verification import Contract, HexDigest, VerificationReport, Zatoshis
from zecsolve.schemas.workflow_verification import (
    OfflineEvaluationV1,
    UTCRecord,
)


class ReviewerCaseV1(UTCRecord):
    state: CaseState
    version: int
    created_at: AwareDatetime


class ReviewerInvoiceV1(Contract):
    terms: InvoiceTermsV1
    policy: InvoicePolicyV1


class ReviewerClaimV1(UTCRecord):
    claim_id: uuid.UUID
    reported_txid: str | None
    note: str | None
    created_at: AwareDatetime
    assertion: Literal[True] = True


class ReviewerEvidenceV1(UTCRecord):
    schema_version: Literal["reviewer-evidence-v1"] = "reviewer-evidence-v1"
    evidence_id: uuid.UUID
    submitted_at: AwareDatetime
    source: str
    source_kind: str
    receipt_sha256: HexDigest | None
    raw_tx_hex_sha256: HexDigest | None
    disclosure: Literal["SELECTED_CONSENTED_EVIDENCE"] = "SELECTED_CONSENTED_EVIDENCE"


class EvidenceContentV1(Contract):
    schema_version: Literal["evidence-content-v1"] = "evidence-content-v1"
    evidence_id: uuid.UUID
    receipt_json: str | None = Field(repr=False)
    raw_tx_hex: str | None = Field(repr=False)


class ReviewerVerificationV1(Contract):
    verification_id: uuid.UUID
    evidence_id: uuid.UUID
    result: VerificationReport


class ReviewerObservationV1(DecisionObservationV1):
    schema_version: Literal["reviewer-observation-v1"] = "reviewer-observation-v1"
    projection: Literal[True] = True


class ReviewerEvaluationV1(UTCRecord):
    verification_id: uuid.UUID
    evaluated_at: AwareDatetime
    result: OfflineEvaluationV1
    historical: Literal[True] = True


class ReviewerDecisionV1(UTCRecord):
    resolution_id: uuid.UUID
    verification_id: uuid.UUID | None
    action: str
    reason: str
    decided_at: AwareDatetime
    allocated_zat: Zatoshis
    source_kind: Literal["OFFLINE", "SIMULATED", "RPC"] | None


class ReviewerEventV1(UTCRecord):
    event_id: uuid.UUID
    action: str
    at: AwareDatetime
    projection: Literal[True] = True


class ReviewerReportV1(UTCRecord):
    schema_version: Literal["reviewer-report-v1"] = "reviewer-report-v1"
    disclosure_scope: Literal["REVIEWER_SCOPED"] = "REVIEWER_SCOPED"
    case_id: uuid.UUID
    generated_at: AwareDatetime
    sections: list[ReportSection]
    limitations: list[str] = Field(
        default_factory=lambda: [
            "SELECTED_FIELDS_ONLY",
            "UNSELECTED_OR_UNCONSENTED_MATERIAL_OMITTED",
            "HISTORICAL_OBSERVATIONS_ARE_NOT_FRESH_CONFIRMATION",
            "PROJECTED_HISTORY_IS_NOT_A_COMPLETE_AUDIT_CHAIN",
        ]
    )
    case: ReviewerCaseV1 | None = None
    invoice: ReviewerInvoiceV1 | None = None
    claims: list[ReviewerClaimV1] | None = None
    evidence: list[ReviewerEvidenceV1] | None = None
    verifications: list[ReviewerVerificationV1] | None = None
    observations: list[ReviewerObservationV1] | None = None
    evaluations: list[ReviewerEvaluationV1] | None = None
    balances: OfflineEvaluationV1 | None = None
    decisions: list[ReviewerDecisionV1] | None = None
    events: list[ReviewerEventV1] | None = None
