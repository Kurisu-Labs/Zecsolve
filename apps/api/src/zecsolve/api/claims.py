import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from zecsolve.api.workflow import execute
from zecsolve.auth.dependencies import require_actor
from zecsolve.schemas.submission import ClaimSubmitRequest, SubmissionAcknowledgementV1
from zecsolve.services.claims import ClaimService

router = APIRouter(prefix="/api/cases/{case_id}/claims", tags=["claims"])


@router.post(
    "",
    response_model=SubmissionAcknowledgementV1,
    status_code=201,
    responses={200: {"model": SubmissionAcknowledgementV1}},
)
def submit_claim(
    case_id: uuid.UUID,
    payload: ClaimSubmitRequest,
    request: Request,
    principal: Annotated[object, Depends(require_actor)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    result, replayed = execute(
        lambda: ClaimService(request.app.state.engine).submit(
            principal, case_id, payload, idempotency_key
        ),
        "CLAIM",
    )
    return JSONResponse(
        status_code=200 if replayed else 201,
        content=result.model_dump(mode="json"),
        headers={"Idempotency-Replayed": str(replayed).lower()},
    )
