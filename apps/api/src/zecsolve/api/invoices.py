import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from zecsolve.api.workflow import execute
from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.auth.dependencies import require_merchant
from zecsolve.schemas.invoice import InvoiceCreateRequest, InvoiceSnapshotV1
from zecsolve.services.invoices import InvoiceService

router = APIRouter(prefix="/api/invoices", tags=["invoices"])
Principal = Annotated[MerchantPrincipal, Depends(require_merchant)]


def service(request: Request) -> InvoiceService:
    return InvoiceService(
        request.app.state.engine, request.app.state.normalizer, request.app.state.verifier_slots
    )


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
    snapshot, replayed = execute(
        lambda: workflow.create(principal, payload, idempotency_key), "INVOICE"
    )
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
    return execute(lambda: workflow.get(principal, invoice_id), "INVOICE")
