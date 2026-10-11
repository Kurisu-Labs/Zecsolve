import uuid
from datetime import UTC
from typing import Annotated, Any, Literal

from pydantic import AwareDatetime, Field, field_validator, model_validator

from zecsolve.schemas.verification import Contract, HexDigest


class ClaimSubmitRequest(Contract):
    reported_txid: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None
    note: Annotated[str, Field(max_length=4096)] | None = Field(default=None, repr=False)
    disclosure_version: Literal["claim-disclosure-v1"]
    processing_authorized: Literal[True]
    share_with_reviewers: bool = False

    @field_validator("processing_authorized", "share_with_reviewers", mode="before")
    @classmethod
    def explicit_boolean(cls, value):
        if type(value) is not bool:
            raise ValueError("Consent must be an explicit boolean")
        return value

    @field_validator("note")
    @classmethod
    def bounded_note(cls, value):
        if value is not None and (len(value.encode("utf-8")) > 4096 or "\0" in value):
            raise ValueError("Invalid claim note")
        return value

    @model_validator(mode="after")
    def claim_has_content(self):
        if self.reported_txid is None and not (self.note and self.note.strip()):
            raise ValueError("A reported transaction ID or note is required")
        return self


class SubmissionAcknowledgementV1(Contract):
    schema_version: Literal["1"] = "1"
    status: Literal["accepted"] = "accepted"
    operation: Literal["claim", "evidence"]
    submission_id: uuid.UUID
    accepted_at: AwareDatetime

    @field_validator("accepted_at")
    @classmethod
    def utc_time(cls, value):
        return value.astimezone(UTC)


class ClaimEventPayload(Contract):
    claim_id: uuid.UUID
    request_sha256: HexDigest
    disclosure_version: Literal["claim-disclosure-v1"]
    processing_authorized: Literal[True]
    share_with_reviewers: bool
    case_version: Annotated[int, Field(strict=True, ge=2)]
    case_state: Literal["OPEN", "AWAITING_EVIDENCE", "UNDER_REVIEW"]


class EvidenceEventPayload(Contract):
    evidence_id: uuid.UUID
    payload_sha256: HexDigest
    consent_id: uuid.UUID
    claim_id: uuid.UUID | None
    case_version: Annotated[int, Field(strict=True, ge=2)]
    case_state: Literal["OPEN", "AWAITING_EVIDENCE", "UNDER_REVIEW"]


class SubmissionEventV2(Contract):
    schema_version: Literal["2"] = "2"
    event_id: uuid.UUID
    case_id: uuid.UUID
    sequence: Annotated[int, Field(strict=True, ge=2)]
    actor: Annotated[str, Field(pattern=r"^(credential|grant):[0-9a-f-]{36}$")]
    action: Literal["CLAIM_SUBMITTED", "EVIDENCE_SUBMITTED"]
    at: AwareDatetime
    payload: dict[str, Any]
    payload_hash: HexDigest
    previous_hash: HexDigest
    event_hash: HexDigest

    @field_validator("at")
    @classmethod
    def utc_time(cls, value):
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def references_and_consent_only(self):
        model = ClaimEventPayload if self.action == "CLAIM_SUBMITTED" else EvidenceEventPayload
        payload = model.model_validate(self.payload)
        if payload.case_version != self.sequence:
            raise ValueError("Event version mismatch")
        # Validate without normalizing persisted hash inputs.
        if payload.model_dump(mode="json") != self.payload:
            raise ValueError("Noncanonical submission event")
        uuid.UUID(self.actor.split(":", 1)[1])
        return self
