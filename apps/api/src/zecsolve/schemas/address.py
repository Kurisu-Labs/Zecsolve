from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from zecsolve.schemas.verification import Contract, HexDigest

MAX_ADDRESS_BYTES = 1024
MAX_ADDRESS_REQUEST_BYTES = 8192


class NormalizeAddressRequest(Contract):
    address: Annotated[str, Field(min_length=1, max_length=MAX_ADDRESS_BYTES)]
    network: Literal["mainnet"]
    pool: Literal["orchard", "sapling"]

    @field_validator("address")
    @classmethod
    def bounded_utf8(cls, value: str) -> str:
        if len(value.encode("utf-8")) > MAX_ADDRESS_BYTES:
            raise ValueError("Address exceeds the byte limit")
        return value


class NormalizedReceiver(Contract):
    network: Literal["mainnet"]
    pool: Literal["orchard", "sapling"]
    receiver_hex: Annotated[str, Field(pattern=r"^[0-9a-f]{86}$")]


class AddressNormalizationReport(Contract):
    schema_version: Literal["1"] = "1"
    state: Literal["VALID", "INVALID", "UNSUPPORTED", "UNAVAILABLE", "ERROR"]
    reason_code: Annotated[str, Field(pattern=r"^[A-Z_]+$", max_length=80)]
    input_sha256: HexDigest | None = None
    receiver: NormalizedReceiver | None = None

    @model_validator(mode="after")
    def consistent_receiver(self):
        valid = self.state == "VALID"
        if valid != (self.receiver is not None) or valid != (
            self.reason_code == "ADDRESS_NORMALIZED"
        ):
            raise ValueError("Receiver and reason must agree with normalization state")
        if valid and self.input_sha256 is None:
            raise ValueError("Successful normalization must bind its input")
        return self
