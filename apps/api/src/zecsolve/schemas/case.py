import uuid
from datetime import UTC
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, field_validator

from zecsolve.domain.statuses import CaseState
from zecsolve.schemas.verification import Contract, HexDigest

MAX_CASE_PAGE_SIZE = 100
MAX_CASE_CURSOR_LENGTH = 512
CaseCursorToken = Annotated[
    str, Field(min_length=1, max_length=MAX_CASE_CURSOR_LENGTH, pattern=r"^[A-Za-z0-9_-]+$")
]


class CaseListQuery(Contract):
    limit: Annotated[int, Field(ge=1, le=MAX_CASE_PAGE_SIZE)] = 50
    state: CaseState | None = None
    cursor: CaseCursorToken | None = None


class CaseCreateRequest(Contract):
    invoice_id: uuid.UUID


class CaseOpeningEventV1(Contract):
    schema_version: Literal["1"] = "1"
    event_id: uuid.UUID
    case_id: uuid.UUID
    sequence: Literal[1] = 1
    actor: Annotated[str, Field(pattern=r"^credential:[0-9a-f-]{36}$")]
    action: Literal["CASE_OPENED"] = "CASE_OPENED"
    at: AwareDatetime
    payload: dict[str, str]
    payload_hash: HexDigest
    previous_hash: None = None
    event_hash: HexDigest

    @field_validator("at")
    @classmethod
    def utc_time(cls, value):
        return value.astimezone(UTC)

    @field_validator("payload")
    @classmethod
    def opening_references_only(cls, value):
        if set(value) != {"invoice_id", "invoice_snapshot_hash", "policy_id"}:
            raise ValueError("Opening payload must contain only invoice and policy references")
        uuid.UUID(value["invoice_id"])
        uuid.UUID(value["policy_id"])
        checksum = value["invoice_snapshot_hash"]
        if len(checksum) != 64 or any(char not in "0123456789abcdef" for char in checksum):
            raise ValueError("Invalid invoice snapshot hash")
        return value


class CaseSummaryV1(Contract):
    schema_version: Literal["1"] = "1"
    case_id: uuid.UUID
    invoice_id: uuid.UUID
    merchant_id: uuid.UUID
    state: CaseState
    version: Annotated[int, Field(strict=True, ge=1)]
    created_at: AwareDatetime

    @field_validator("created_at")
    @classmethod
    def utc_time(cls, value):
        return value.astimezone(UTC)


class CaseOpenedV1(CaseSummaryV1):
    state: Literal["OPEN"] = "OPEN"
    version: Literal[1] = 1
    opening_event: CaseOpeningEventV1


class CaseDetailV1(CaseSummaryV1):
    # Current state is separate from the immutable opening outcome returned on retries.
    opening_event: CaseOpeningEventV1


class CaseListV1(Contract):
    schema_version: Literal["1"] = "1"
    items: Annotated[list[CaseSummaryV1], Field(max_length=MAX_CASE_PAGE_SIZE)]
    next_cursor: CaseCursorToken | None = None
