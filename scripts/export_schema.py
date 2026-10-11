"""Regenerate versioned service and verifier JSON contracts."""

import json
from pathlib import Path

from zecsolve.schemas.address import AddressNormalizationReport, NormalizeAddressRequest
from zecsolve.schemas.case import CaseCreateRequest, CaseDetailV1, CaseOpenedV1
from zecsolve.schemas.evidence import (
    EvidenceStoredV1,
    EvidenceSubmitRequest,
    EvidenceSubmittedEventV1,
)
from zecsolve.schemas.invoice import InvoiceCreateRequest, InvoiceSnapshotV1
from zecsolve.schemas.resolution import MerchantCaseReportV1, ResolutionOutcomeV1, ResolveRequest
from zecsolve.schemas.verification import VerificationReport
from zecsolve.schemas.workflow_verification import (
    CaseReportV1,
    CaseVerifyRequest,
    VerificationAttemptV1,
)

root = Path(__file__).resolve().parents[1]
for name, model in (
    ("verifier-result", VerificationReport),
    ("normalize-address-request", NormalizeAddressRequest),
    ("normalize-address-result", AddressNormalizationReport),
    ("invoice-create-request", InvoiceCreateRequest),
    ("invoice-snapshot", InvoiceSnapshotV1),
    ("case-create-request", CaseCreateRequest),
    ("case-opened", CaseOpenedV1),
    ("case-detail", CaseDetailV1),
    ("evidence-submit-request", EvidenceSubmitRequest),
    ("evidence-stored", EvidenceStoredV1),
    ("evidence-submitted-event", EvidenceSubmittedEventV1),
    ("case-verify-request", CaseVerifyRequest),
    ("verification-attempt", VerificationAttemptV1),
    ("case-report", CaseReportV1),
    ("case-resolve-request", ResolveRequest),
    ("resolution-outcome", ResolutionOutcomeV1),
    ("merchant-case-report", MerchantCaseReportV1),
):
    target = root / f"contracts/{name}.schema.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(model.model_json_schema(), indent=2) + "\n")
