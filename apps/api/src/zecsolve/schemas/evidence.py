import uuid
from datetime import UTC
from typing import Annotated, Literal

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
