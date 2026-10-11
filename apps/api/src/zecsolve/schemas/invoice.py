import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, ConfigDict, Field, field_validator

from zecsolve.domain.rules import RULES_VERSION
from zecsolve.schemas.verification import MAX_ZAT, Contract, HexDigest


class InvoiceCreateRequest(Contract):
    expected_zat: Annotated[int, Field(strict=True, gt=0, le=MAX_ZAT)]
    network: Literal["mainnet"]
    pool: Literal["orchard", "sapling"]
    receiver_address: Annotated[str, Field(min_length=1, max_length=1024)]
    expected_memo: Annotated[str, Field(max_length=512)] | None = None
    expires_at: AwareDatetime | None = None

    @field_validator("receiver_address", "expected_memo")
    @classmethod
    def bounded_utf8(cls, value, info):
        if value is not None:
            limit = 512 if info.field_name == "expected_memo" else 1024
            if len(value.encode("utf-8")) > limit:
                raise ValueError("Text exceeds UTF-8 byte limit")
        return value

    @field_validator("expires_at", mode="before")
    @classmethod
    def explicit_datetime(cls, value):
        if value is not None and not isinstance(value, (str, datetime)):
            raise ValueError("Use a timezone-aware timestamp")
        return value

    @field_validator("expires_at")
    @classmethod
    def utc_expiry(cls, value):
        try:
            return value.astimezone(UTC) if value else None
        except (OverflowError, ValueError) as error:
            raise ValueError("Invalid UTC timestamp") from error

    @property
    def memo_bytes(self) -> bytes | None:
        return (
            self.expected_memo.encode("utf-8").ljust(512, b"\0")
            if self.expected_memo is not None
            else None
        )


class InvoicePolicyV1(Contract):
    model_config = ConfigDict(extra="forbid", frozen=True)
    policy_version: Literal["invoice-policy-v1"] = "invoice-policy-v1"
    rules_version: str = RULES_VERSION
    minimum_confirmations: Annotated[int, Field(strict=True, gt=0)] = 10
    max_observation_age_seconds: Annotated[int, Field(strict=True, gt=0)] = 60
    memo_binding: Literal["exact"] = "exact"
    allow_overpayment: Literal[False] = False
    unique_receiver_binding: Literal[False] = False


class InvoiceTermsV1(InvoiceCreateRequest):
    receiver_hex: Annotated[str, Field(pattern=r"^[0-9a-f]{86}$")]
    memo_hex: Annotated[str, Field(pattern=r"^[0-9a-f]{1024}$")] | None


class InvoiceSnapshotV1(Contract):
    schema_version: Literal["1"] = "1"
    invoice_id: uuid.UUID
    merchant_id: uuid.UUID
    policy_id: uuid.UUID
    created_at: AwareDatetime
    terms: InvoiceTermsV1
    policy: InvoicePolicyV1
    snapshot_hash: HexDigest
