from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from zecsolve.domain.statuses import ReceiptState

MAX_ZAT = 2_100_000_000_000_000
Zatoshis = Annotated[int, Field(strict=True, ge=0, le=MAX_ZAT)]
HexDigest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VerifierIdentity(Contract):
    name: Literal["zecsolve-verifier"] = "zecsolve-verifier"
    version: str = "0.1.0"
    glasspane_revision: Literal["f6468e6d08a7adad53bf2991a311358dc84e869b"] = (
        "f6468e6d08a7adad53bf2991a311358dc84e869b"
    )


class RecoveredOutput(Contract):
    network: Literal["mainnet"]
    pool: Literal["orchard", "sapling"]
    txid: HexDigest
    output_index: Annotated[int, Field(strict=True, ge=0, le=2**32 - 1)]
    amount_zat: Zatoshis
    receiver_hex: Annotated[str, Field(pattern=r"^[0-9a-f]{86}$")]
    receiver_address: Annotated[str, Field(min_length=1, max_length=1024)]
    memo_hex: Annotated[str, Field(pattern=r"^[0-9a-f]{1024}$")]

    @property
    def identity(self) -> str:
        return f"{self.network}:{self.pool}:{self.txid}:{self.output_index}"


class VerificationReport(Contract):
    schema_version: Literal["1"] = "1"
    verifier: VerifierIdentity = Field(default_factory=VerifierIdentity)
    receipt_state: ReceiptState
    # This offline verifier cannot assert inclusion or confirmations.
    chain_state: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    reason_code: Annotated[str, Field(pattern=r"^[A-Z_]+$", max_length=80)]
    raw_tx_verified: bool = False
    signature_state: Literal["NONE", "VALID", "INVALID"] = "NONE"
    receipt_sha256: HexDigest | None = None
    raw_tx_sha256: HexDigest | None = None
    output: RecoveredOutput | None = None

    @model_validator(mode="after")
    def consistent_recovery(self):
        valid = self.receipt_state == ReceiptState.VALID
        if valid != self.raw_tx_verified or valid != (self.output is not None):
            raise ValueError("Recovery fields must agree with receipt validity")
        if valid and (not self.receipt_sha256 or not self.raw_tx_sha256):
            raise ValueError("Valid recovery must bind both input hashes")
        return self


class VerifyRequest(Contract):
    # Preserve exact receipt bytes for provenance. JSON is parsed only inside the Rust verifier.
    receipt_json: Annotated[str, Field(max_length=16_384)] | None = None
    raw_tx_hex: Annotated[str, Field(max_length=4_000_002)] | None = None

    @field_validator("receipt_json", "raw_tx_hex")
    @classmethod
    def valid_utf8(cls, value):
        if value is not None:
            value.encode("utf-8")
        return value
