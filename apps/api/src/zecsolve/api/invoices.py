import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.auth.dependencies import require_merchant
from zecsolve.schemas.invoice import InvoiceCreateRequest, InvoiceSnapshotV1
from zecsolve.services.invoices import InvoiceError, InvoiceService

router = APIRouter(prefix="/api/invoices", tags=["invoices"])
Principal = Annotated[MerchantPrincipal, Depends(require_merchant)]


def service(request: Request) -> InvoiceService:
    return InvoiceService(
        request.app.state.engine, request.app.state.normalizer, request.app.state.verifier_slots
    )


def execute(operation):
    try:
        return operation()
    except InvoiceError as error:
        headers = {"WWW-Authenticate": "Bearer"} if error.status == 401 else None
        raise HTTPException(error.status, error.code, headers=headers) from None
    except SQLAlchemyError as error:
        if getattr(getattr(error, "orig", None), "sqlstate", None) in ("55P03", "40P01", "40001"):
            raise HTTPException(409, "RETRY_INVOICE_OPERATION") from None
        raise HTTPException(503, "INVOICE_SERVICE_UNAVAILABLE") from None


@router.post(
    "",
    response_model=InvoiceSnapshotV1,
    status_code=201,
    responses={200: {"model": InvoiceSnapshotV1}},
)
def create_invoice(
    payload: InvoiceCreateRequest,
    principal: Principal,
    workflow: Annotated[InvoiceService, Depends(service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    snapshot, replayed = execute(lambda: workflow.create(principal, payload, idempotency_key))
    return JSONResponse(
        status_code=200 if replayed else 201,
        content=snapshot.model_dump(mode="json"),
        headers={
            "Location": f"/api/invoices/{snapshot.invoice_id}",
            "Idempotency-Replayed": str(replayed).lower(),
        },
    )


@router.get("/{invoice_id}", response_model=InvoiceSnapshotV1)
def get_invoice(
    invoice_id: uuid.UUID,
    principal: Principal,
    workflow: Annotated[InvoiceService, Depends(service)],
):
    return execute(lambda: workflow.get(principal, invoice_id))
