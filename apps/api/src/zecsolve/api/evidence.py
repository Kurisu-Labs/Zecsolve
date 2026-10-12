import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from zecsolve.api.workflow import execute
from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.auth.dependencies import require_actor, require_merchant
from zecsolve.schemas.disclosure import EvidenceContentV1, ReviewerEvidenceV1
from zecsolve.schemas.evidence import (
    EvidenceStoredV1,
    EvidenceStoredV2,
    EvidenceSubmitRequest,
    EvidenceSubmitRequestV2,
)
from zecsolve.schemas.submission import SubmissionAcknowledgementV1
from zecsolve.services.evidence import EvidenceService

router = APIRouter(prefix="/api/cases/{case_id}/evidence", tags=["evidence"])
Principal = Annotated[MerchantPrincipal, Depends(require_merchant)]


def service(request: Request) -> EvidenceService:
    return EvidenceService(
        request.app.state.engine,
        request.app.state.evidence_cipher,
        request.app.state.verifier_slots,
    )


@router.post(
    "",
    response_model=EvidenceStoredV1 | SubmissionAcknowledgementV1,
    status_code=201,
    responses={200: {"model": EvidenceStoredV1 | SubmissionAcknowledgementV1}},
)
def submit_evidence(
    case_id: uuid.UUID,
    payload: EvidenceSubmitRequest | EvidenceSubmitRequestV2,
    principal: Annotated[object, Depends(require_actor)],
    workflow: Annotated[EvidenceService, Depends(service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    result, replayed = execute(
        lambda: workflow.submit(principal, case_id, payload, idempotency_key), "EVIDENCE"
    )
    headers = {"Idempotency-Replayed": str(replayed).lower()}
    if isinstance(result, EvidenceStoredV2):
        result = SubmissionAcknowledgementV1(
            operation="evidence",
            submission_id=result.evidence_id,
            accepted_at=result.submitted_at,
        )
    else:
        headers["Location"] = f"/api/cases/{case_id}/evidence/{result.evidence_id}"
    return JSONResponse(
        status_code=200 if replayed else 201,
        content=result.model_dump(mode="json"),
        headers=headers,
    )


@router.get(
    "/{evidence_id}", response_model=EvidenceStoredV1 | EvidenceStoredV2 | ReviewerEvidenceV1
)
def get_evidence(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    principal: Annotated[object, Depends(require_actor)],
    workflow: Annotated[EvidenceService, Depends(service)],
):
    return execute(lambda: workflow.get(principal, case_id, evidence_id), "EVIDENCE")


@router.get("/{evidence_id}/content", response_model=EvidenceContentV1)
def get_evidence_content(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    principal: Annotated[object, Depends(require_actor)],
    workflow: Annotated[EvidenceService, Depends(service)],
):
    content = execute(lambda: workflow.read_content(principal, case_id, evidence_id), "EVIDENCE")
    return EvidenceContentV1(
        evidence_id=evidence_id, receipt_json=content.receipt_json, raw_tx_hex=content.raw_tx_hex
    )
