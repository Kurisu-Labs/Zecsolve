import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from zecsolve.api.workflow import execute
from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.auth.dependencies import require_actor, require_merchant
from zecsolve.schemas.disclosure import ReviewerReportV1
from zecsolve.schemas.resolution import MerchantCaseReportV1
from zecsolve.schemas.workflow_verification import (
    CaseVerifyRequest,
    VerificationAttemptV1,
)
from zecsolve.services.reports import CaseReportService
from zecsolve.services.verifications import VerificationService

router = APIRouter(prefix="/api/cases/{case_id}", tags=["verification"])
Principal = Annotated[MerchantPrincipal, Depends(require_merchant)]


def service(request: Request):
    return VerificationService(
        request.app.state.engine,
        request.app.state.evidence_cipher,
        request.app.state.verifier,
        request.app.state.verifier_slots,
    )


@router.post(
    "/verify",
    response_model=VerificationAttemptV1,
    status_code=201,
    responses={200: {"model": VerificationAttemptV1}},
)
def verify_evidence(
    case_id: uuid.UUID,
    payload: CaseVerifyRequest,
    principal: Principal,
    workflow: Annotated[VerificationService, Depends(service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    result, replayed = execute(
        lambda: workflow.verify(principal, case_id, payload, idempotency_key), "VERIFICATION"
    )
    return JSONResponse(
        status_code=200 if replayed else 201,
        content=result.model_dump(mode="json"),
        headers={
            "Location": f"/api/cases/{case_id}/report?verification_id={result.verification_id}",
            "Idempotency-Replayed": str(replayed).lower(),
        },
    )


@router.get("/report", response_model=MerchantCaseReportV1 | ReviewerReportV1)
def case_report(
    case_id: uuid.UUID,
    principal: Annotated[object, Depends(require_actor)],
    request: Request,
    verification_id: uuid.UUID | None = None,
):
    result = execute(
        lambda: CaseReportService(request.app.state.engine).get(
            principal, case_id, verification_id
        ),
        "REPORT",
    )

    if isinstance(result, ReviewerReportV1):
        return JSONResponse(
            content={
                key: value
                for key, value in result.model_dump(mode="json").items()
                if value is not None
            }
        )
    return result
