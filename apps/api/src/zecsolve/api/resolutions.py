import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from zecsolve.api.workflow import execute
from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.auth.dependencies import require_merchant
from zecsolve.schemas.resolution import ResolveRequest, ResolutionOutcomeV1
from zecsolve.services.resolutions import ResolutionService

router = APIRouter(prefix="/api/cases/{case_id}", tags=["resolution"])


def service(request: Request):
    # No simulated observer or trust-policy toggle is composed into the ASGI app.
    return ResolutionService(request.app.state.engine)


@router.post(
    "/resolve",
    response_model=ResolutionOutcomeV1,
    status_code=201,
    responses={200: {"model": ResolutionOutcomeV1}},
)
def resolve_case(
    case_id: uuid.UUID,
    payload: ResolveRequest,
    principal: Annotated[MerchantPrincipal, Depends(require_merchant)],
    workflow: Annotated[ResolutionService, Depends(service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    result, replayed = execute(
        lambda: workflow.resolve(principal, case_id, payload, idempotency_key), "RESOLUTION"
    )
    return JSONResponse(
        status_code=200 if replayed else 201,
        content=result.model_dump(mode="json"),
        headers={
            "Location": f"/api/cases/{case_id}/report",
            "Idempotency-Replayed": str(replayed).lower(),
        },
    )
