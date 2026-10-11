import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from zecsolve.api.workflow import execute
from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.auth.dependencies import require_merchant
from zecsolve.schemas.resolution import DecisionObservation, RefreshChainRequest
from zecsolve.services.observations import ObservationService

router = APIRouter(prefix="/api/cases/{case_id}", tags=["chain"])


@router.post(
    "/chain-observations",
    response_model=DecisionObservation,
    status_code=201,
    responses={200: {"model": DecisionObservation}},
)
def refresh_chain(
    case_id: uuid.UUID,
    payload: RefreshChainRequest,
    request: Request,
    principal: Annotated[MerchantPrincipal, Depends(require_merchant)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    service = ObservationService(request.app.state.engine, request.app.state.chain_observer)
    result, replayed = execute(
        lambda: service.refresh_request(
            principal, case_id, payload.verification_id, idempotency_key
        ),
        "OBSERVATION",
    )
    return JSONResponse(
        status_code=200 if replayed else 201,
        content=result.model_dump(mode="json"),
        headers={"Idempotency-Replayed": str(replayed).lower()},
    )
