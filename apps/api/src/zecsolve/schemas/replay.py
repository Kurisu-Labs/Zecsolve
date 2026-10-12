from typing import Literal

from zecsolve.schemas.verification import Contract, HexDigest


class ReplayCheckV1(Contract):
    category: Literal["integrity", "cryptographic_recovery", "rules", "context"]
    reference: str
    status: Literal["PASS", "FAIL", "MISSING", "UNSUPPORTED", "EXTERNAL"]
    code: str


class ReplayResultV1(Contract):
    schema_version: Literal["case-replay-v1"] = "case-replay-v1"
    status: Literal["REPRODUCED", "LIMITED", "UNSUPPORTED", "FAILED"]
    full_replay: bool
    packet_file_sha256: HexDigest
    checks: list[ReplayCheckV1]
    external_assertions: list[str]
