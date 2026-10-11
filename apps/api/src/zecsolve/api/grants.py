import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from zecsolve.api.workflow import execute
from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.auth.dependencies import require_merchant
from zecsolve.schemas.grant import GrantCreatedV1, GrantCreateRequest, GrantListV1, GrantMetadataV1
from zecsolve.services.grants import GrantService

router = APIRouter(prefix="/api/cases/{case_id}/grants", tags=["grants"])
Principal = Annotated[MerchantPrincipal, Depends(require_merchant)]


def service(request: Request):
    return GrantService(request.app.state.engine)


@router.post(
    "", response_model=GrantCreatedV1, status_code=201, responses={200: {"model": GrantCreatedV1}}
)
def create_grant(
    case_id: uuid.UUID,
    payload: GrantCreateRequest,
    principal: Principal,
    workflow: Annotated[GrantService, Depends(service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    result, replayed = execute(
        lambda: workflow.create(principal, case_id, payload, idempotency_key), "GRANT"
    )
    return JSONResponse(
        status_code=200 if replayed else 201,
        content=result.model_dump(mode="json"),
        headers={
            "Location": f"/api/cases/{case_id}/grants",
            "Idempotency-Replayed": str(replayed).lower(),
        },
    )


@router.get("", response_model=GrantListV1)
def list_grants(
    case_id: uuid.UUID, principal: Principal, workflow: Annotated[GrantService, Depends(service)]
):
    return execute(lambda: workflow.list(principal, case_id), "GRANT")


@router.delete("/{grant_id}", response_model=GrantMetadataV1)
def revoke_grant(
    case_id: uuid.UUID,
    grant_id: uuid.UUID,
    principal: Principal,
    workflow: Annotated[GrantService, Depends(service)],
):
    return execute(lambda: workflow.revoke(principal, case_id, grant_id), "GRANT")
