import uuid
from datetime import UTC
from typing import Annotated, Any, Literal

from pydantic import AwareDatetime, Field, field_validator

from zecsolve.domain.statuses import CaseState
from zecsolve.schemas.verification import Contract, HexDigest

MAX_EVIDENCE_PAYLOAD_BYTES = 4_200_000


class EvidenceSubmitRequest(Contract):
    receipt_json: Annotated[str, Field(max_length=16_384)] | None = Field(default=None, repr=False)
    raw_tx_hex: Annotated[str, Field(max_length=4_000_002)] | None = Field(default=None, repr=False)
    source: Annotated[str, Field(min_length=1, max_length=200)]
    source_kind: Literal["public_fixture", "merchant_submission"] = "merchant_submission"
    disclosure_version: Literal["evidence-disclosure-v1"] = "evidence-disclosure-v1"
    processing_authorized: Literal[True]
    share_with_reviewers: Literal[False] = False

    @field_validator("processing_authorized", "share_with_reviewers", mode="before")
    @classmethod
    def explicit_boolean(cls, value):
        if type(value) is not bool:
            raise ValueError("Acknowledgement must be an explicit boolean")
        return value

    @field_validator("receipt_json", "raw_tx_hex", "source")
    @classmethod
    def bounded_utf8(cls, value, info):
        if value is not None:
            limit = {"receipt_json": 16_384, "raw_tx_hex": 4_000_002, "source": 200}[
                info.field_name
            ]
            if len(value.encode("utf-8")) > limit:
                raise ValueError("Input exceeds UTF-8 byte limit")
            if info.field_name == "source" and ("\0" in value or not value.strip()):
                raise ValueError("Invalid source label")
        return value


class EvidenceStoredV1(Contract):
    schema_version: Literal["1"] = "1"
    evidence_id: uuid.UUID
    case_id: uuid.UUID
    merchant_id: uuid.UUID
    submitted_by: uuid.UUID
    submitted_at: AwareDatetime
    source: str
    source_kind: Literal["public_fixture", "merchant_submission"]
    disclosure_version: Literal["evidence-disclosure-v1"]
    processing_authorized: Literal[True]
    share_with_reviewers: Literal[False]
    receipt_sha256: HexDigest | None
    raw_tx_hex_sha256: HexDigest | None
    payload_sha256: HexDigest
    case_version: Annotated[int, Field(strict=True, ge=2)]
    case_state: CaseState
    event_id: uuid.UUID

    @field_validator("submitted_at")
    @classmethod
    def utc_time(cls, value):
        return value.astimezone(UTC)


class EvidenceSubmittedEventV1(Contract):
    schema_version: Literal["1"] = "1"
    event_id: uuid.UUID
    case_id: uuid.UUID
    sequence: Annotated[int, Field(strict=True, ge=2)]
    actor: Annotated[str, Field(pattern=r"^credential:[0-9a-f-]{36}$")]
    action: Literal["EVIDENCE_SUBMITTED"] = "EVIDENCE_SUBMITTED"
    at: AwareDatetime
    payload: dict[str, Any]
    payload_hash: HexDigest
    previous_hash: HexDigest
    event_hash: HexDigest

    @field_validator("at")
    @classmethod
    def utc_time(cls, value):
        return value.astimezone(UTC)

    @field_validator("payload")
    @classmethod
    def submission_references_only(cls, value):
        if set(value) != {"evidence_id", "payload_sha256", "case_version", "case_state"}:
            raise ValueError("Invalid evidence audit payload")
        uuid.UUID(value["evidence_id"])
        checksum = value["payload_sha256"]
        if (
            not isinstance(checksum, str)
            or len(checksum) != 64
            or any(c not in "0123456789abcdef" for c in checksum)
        ):
            raise ValueError("Invalid payload hash")
        if type(value["case_version"]) is not int or value["case_version"] < 2:
            raise ValueError("Invalid case version")
        if value["case_state"] not in ("OPEN", "AWAITING_EVIDENCE", "UNDER_REVIEW"):
            raise ValueError("Invalid submission state")
        return value
