"""Regenerate versioned service and verifier JSON contracts."""

import json
from pathlib import Path

from zecsolve.schemas.access import AccessContextV1, GrantScopeV1
from zecsolve.schemas.address import AddressNormalizationReport, NormalizeAddressRequest
from zecsolve.schemas.case import (
    CaseCreateRequest,
    CaseDetailV1,
    CaseListQuery,
    CaseListV1,
    CaseOpenedV1,
)
from zecsolve.schemas.disclosure import EvidenceContentV1, ReviewerEvidenceV1, ReviewerReportV1
from zecsolve.schemas.evidence import (
    EvidenceStoredV1,
    EvidenceStoredV2,
    EvidenceSubmitRequest,
    EvidenceSubmitRequestV2,
    EvidenceSubmittedEventV1,
)
from zecsolve.schemas.grant import GrantCreatedV1, GrantCreateRequest, GrantListV1
from zecsolve.schemas.invoice import InvoiceCreateRequest, InvoiceSnapshotV1
from zecsolve.schemas.packet import CasePacketV1
from zecsolve.schemas.replay import ReplayResultV1
from zecsolve.schemas.resolution import (
    DecisionObservationV2,
    MerchantCaseReportV1,
    RefreshChainRequest,
    ResolutionOutcomeV1,
    ResolveRequest,
)
from zecsolve.schemas.session import SessionExchangeRequest, SessionInfoV1
from zecsolve.schemas.submission import (
    ClaimSubmitRequest,
    SubmissionAcknowledgementV1,
    SubmissionEventV2,
)
from zecsolve.schemas.verification import VerificationReport
from zecsolve.schemas.workflow_verification import (
    CaseReportV1,
    CaseVerifyRequest,
    VerificationAttemptV1,
)

root = Path(__file__).resolve().parents[1]
for name, model in (
    ("case-replay", ReplayResultV1),
    ("case-packet", CasePacketV1),
    ("reviewer-report", ReviewerReportV1),
    ("reviewer-evidence", ReviewerEvidenceV1),
    ("evidence-content", EvidenceContentV1),
    ("access-context", AccessContextV1),
    ("grant-scope", GrantScopeV1),
    ("grant-create-request", GrantCreateRequest),
    ("grant-created", GrantCreatedV1),
    ("grant-list", GrantListV1),
    ("session-exchange-request", SessionExchangeRequest),
    ("session-info", SessionInfoV1),
    ("verifier-result", VerificationReport),
    ("normalize-address-request", NormalizeAddressRequest),
    ("normalize-address-result", AddressNormalizationReport),
    ("invoice-create-request", InvoiceCreateRequest),
    ("invoice-snapshot", InvoiceSnapshotV1),
    ("case-create-request", CaseCreateRequest),
    ("case-opened", CaseOpenedV1),
    ("case-detail", CaseDetailV1),
    ("case-list-query", CaseListQuery),
    ("case-list", CaseListV1),
    ("evidence-submit-request", EvidenceSubmitRequest),
    ("evidence-stored", EvidenceStoredV1),
    ("evidence-submitted-event", EvidenceSubmittedEventV1),
    ("evidence-submit-request-v2", EvidenceSubmitRequestV2),
    ("evidence-stored-v2", EvidenceStoredV2),
    ("claim-submit-request", ClaimSubmitRequest),
    ("submission-acknowledgement", SubmissionAcknowledgementV1),
    ("submission-event-v2", SubmissionEventV2),
    ("case-verify-request", CaseVerifyRequest),
    ("verification-attempt", VerificationAttemptV1),
    ("case-report", CaseReportV1),
    ("case-resolve-request", ResolveRequest),
    ("resolution-outcome", ResolutionOutcomeV1),
    ("merchant-case-report", MerchantCaseReportV1),
    ("chain-refresh-request", RefreshChainRequest),
    ("rpc-observation", DecisionObservationV2),
):
    target = root / f"contracts/{name}.schema.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(model.model_json_schema(), indent=2) + "\n")
