import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from zecsolve.api.workflow import execute
from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.auth.dependencies import require_merchant
from zecsolve.schemas.case import CaseCreateRequest, CaseDetailV1, CaseOpenedV1
from zecsolve.services.cases import CaseService

router = APIRouter(prefix="/api/cases", tags=["cases"])
Principal = Annotated[MerchantPrincipal, Depends(require_merchant)]


def service(request: Request) -> CaseService:
    return CaseService(request.app.state.engine)


@router.post(
    "", response_model=CaseOpenedV1, status_code=201, responses={200: {"model": CaseOpenedV1}}
)
def create_case(
    payload: CaseCreateRequest,
    principal: Principal,
    workflow: Annotated[CaseService, Depends(service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    result, replayed = execute(lambda: workflow.create(principal, payload, idempotency_key), "CASE")
    return JSONResponse(
        status_code=200 if replayed else 201,
        content=result.model_dump(mode="json"),
        headers={
            "Location": f"/api/cases/{result.case_id}",
            "Idempotency-Replayed": str(replayed).lower(),
        },
    )


@router.get("/{case_id}", response_model=CaseDetailV1)
def get_case(
    case_id: uuid.UUID, principal: Principal, workflow: Annotated[CaseService, Depends(service)]
):
    return execute(lambda: workflow.get(principal, case_id), "CASE")
