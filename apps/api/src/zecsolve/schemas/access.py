"""Shared permission vocabulary; contexts are server-derived, never authorization inputs."""

import uuid
from typing import Annotated, Literal

from pydantic import Field, StrictBool, model_validator

from zecsolve.schemas.verification import Contract

ReportSection = Literal[
    "case",
    "invoice",
    "claims",
    "evidence",
    "verifications",
    "observations",
    "evaluations",
    "balances",
    "decisions",
    "events",
]
Permission = Literal[
    "case:summary",
    "case:manage",
    "claim:submit",
    "evidence:submit",
    "report:read",
    "evidence:read",
    "case:export",
    "case:verify",
    "case:resolve",
]
MERCHANT_PERMISSIONS = [
    "case:summary",
    "case:manage",
    "claim:submit",
    "evidence:submit",
    "report:read",
    "evidence:read",
    "case:export",
    "case:verify",
    "case:resolve",
]


class GrantScopeV1(Contract):
    role: Literal["customer", "reviewer"]
    report_sections: Annotated[list[ReportSection], Field(max_length=10)] = Field(
        default_factory=list
    )
    evidence_ids: Annotated[list[uuid.UUID], Field(max_length=100)] = Field(default_factory=list)
    allow_export: StrictBool = False

    @model_validator(mode="after")
    def least_privilege(self):
        if self.role == "customer" and (
            self.report_sections or self.evidence_ids or self.allow_export
        ):
            raise ValueError("Customer scope only permits submission and a case summary")
        if self.role == "reviewer" and not self.report_sections:
            raise ValueError("Select at least one reviewer report section")
        if len(set(self.evidence_ids)) != len(self.evidence_ids) or len(
            set(self.report_sections)
        ) != len(self.report_sections):
            raise ValueError("Duplicate scope selections")
        return self


class AccessContextV1(Contract):
    schema_version: Literal["1"] = "1"
    role: Literal["merchant", "customer", "reviewer"]
    merchant_id: uuid.UUID
    credential_id: uuid.UUID | None = None
    grant_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    permissions: list[Permission]
    report_sections: list[ReportSection] = Field(default_factory=list)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    allow_export: StrictBool = False
