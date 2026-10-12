"""Versioned offline interchange; historical records retain their original schemas."""

import base64
import uuid
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, StrictBool, model_validator

from zecsolve.schemas.disclosure import ReviewerReportV1
from zecsolve.schemas.resolution import MerchantCaseReportV1
from zecsolve.schemas.verification import Contract, HexDigest
from zecsolve.schemas.workflow_verification import OwnedAllocationV1

MAX_PACKET_BYTES = 64 * 1024 * 1024
MAX_COMPONENT_BYTES = 4_200_000


class PacketComponentV1(Contract):
    availability: Literal["PRESENT", "NOT_SUBMITTED", "OMITTED"]
    encoding: Literal["base64-utf8"] = "base64-utf8"
    data: Annotated[str, Field(max_length=5_600_000)] | None = Field(repr=False)
    sha256: HexDigest | None
    hash_basis: Literal["original-utf8-bytes"] = "original-utf8-bytes"

    @model_validator(mode="after")
    def exact_representation(self):
        if self.availability == "PRESENT":
            if self.data is None or self.sha256 is None:
                raise ValueError("Present components require data and original-byte hash")
            raw = base64.b64decode(self.data, validate=True)
            if len(raw) > MAX_COMPONENT_BYTES or base64.b64encode(raw).decode("ascii") != self.data:
                raise ValueError("Noncanonical or oversized base64 component")
            raw.decode("utf-8")
        elif self.data is not None or self.sha256 is not None:
            raise ValueError("Absent components cannot disclose bytes or hashes")
        return self

    def text(self):
        return (
            base64.b64decode(self.data, validate=True).decode("utf-8")
            if self.data is not None
            else None
        )


class PacketProvenanceV1(Contract):
    source: str
    source_kind: str
    submitted_at: AwareDatetime
    assertion: Literal[True] = True


class PacketEvidenceV1(Contract):
    evidence_id: uuid.UUID
    provenance: PacketProvenanceV1
    receipt: PacketComponentV1
    raw_transaction_hex: PacketComponentV1
    # Full canonical submission is available to the merchant only; projections
    # cannot disclose private claim links, actor IDs or consent metadata through it.
    submission_payload: PacketComponentV1
    decoded_transaction_sha256: HexDigest | None
    decoded_transaction_hash_basis: Literal["decoded-transaction-bytes"] = (
        "decoded-transaction-bytes"
    )


class PacketVerifierV1(Contract):
    name: str
    version: str | None
    result_schema_version: str | None
    glasspane_revision: str | None


class PacketImplementationsV1(Contract):
    verifiers: list[PacketVerifierV1]
    rules: list[str]


class PacketBalanceContextV1(Contract):
    selected_verification_id: uuid.UUID | None
    approved_allocations: list[OwnedAllocationV1]
    foreign_conflict: StrictBool
    foreign_conflict_basis: Literal["opaque-external-assertion"] = "opaque-external-assertion"


class PacketPayloadV1(Contract):
    disclosure_scope: Literal["MERCHANT", "REVIEWER_SCOPED"]
    replay_scope: Literal["FULL_HISTORY", "LIMITED"]
    omissions: list[str]
    assertions: list[
        Literal[
            "INVOICE_AND_CLAIMS_ARE_BUSINESS_ASSERTIONS",
            "OBSERVATIONS_ARE_HISTORICAL_EXTERNAL_ASSERTIONS",
            "ALLOCATION_AND_SOURCE_AUTHORITY_ARE_EXTERNAL_ASSERTIONS",
            "HASHES_DO_NOT_AUTHENTICATE_AUTHOR",
        ]
    ]
    report: MerchantCaseReportV1 | ReviewerReportV1
    evidence: list[PacketEvidenceV1]
    balance_context: PacketBalanceContextV1 | None
    implementations: PacketImplementationsV1

    @model_validator(mode="after")
    def disclosure_contract(self):
        if len(self.assertions) != 4 or len(set(self.assertions)) != 4:
            raise ValueError("All four external assertion limits must be declared")
        if self.disclosure_scope != self.report.disclosure_scope:
            raise ValueError("Packet/report disclosure mismatch")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise ValueError("Duplicate evidence identity")
        if self.disclosure_scope == "REVIEWER_SCOPED":
            if self.replay_scope != "LIMITED" or self.balance_context is not None:
                raise ValueError("Reviewer projections cannot carry full historical context")
            if any(item.submission_payload.availability != "OMITTED" for item in self.evidence):
                raise ValueError("Reviewer packets cannot disclose complete submission payloads")
        if self.replay_scope == "LIMITED" and not self.omissions:
            raise ValueError("Limited packets must explain their omissions")
        if self.replay_scope == "FULL_HISTORY":
            if self.omissions or self.balance_context is None:
                raise ValueError("Full packets require balance context and no omissions")
            if any(
                component.availability == "OMITTED"
                for item in self.evidence
                for component in (item.receipt, item.raw_transaction_hex, item.submission_payload)
            ):
                raise ValueError("Full packets cannot omit inputs")
            if any(item.submission_payload.availability != "PRESENT" for item in self.evidence):
                raise ValueError("Full packets require submission payloads")
            if {item.evidence_id for item in self.evidence} != {
                item.evidence_id for item in self.report.evidence
            }:
                raise ValueError("Full packet evidence must match report evidence")
        return self


class PacketIntegrityV1(Contract):
    algorithm: Literal["SHA-256"] = "SHA-256"
    canonicalization: Literal["zecsolve-json-v1"] = "zecsolve-json-v1"
    hash_basis: Literal["canonical-json-payload-excluding-integrity"] = (
        "canonical-json-payload-excluding-integrity"
    )
    payload_sha256: HexDigest


class CasePacketV1(Contract):
    schema_version: Literal["case-packet-v1"] = "case-packet-v1"
    payload: PacketPayloadV1
    integrity: PacketIntegrityV1
