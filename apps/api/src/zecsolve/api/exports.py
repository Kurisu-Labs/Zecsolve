import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from zecsolve.api.workflow import execute
from zecsolve.auth.dependencies import require_actor
from zecsolve.schemas.packet import CasePacketV1
from zecsolve.services.exports import CaseExportService

router = APIRouter(prefix="/api/cases/{case_id}", tags=["export"])


@router.get("/export", response_model=CasePacketV1)
def export_case(
    case_id: uuid.UUID,
    principal: Annotated[object, Depends(require_actor)],
    request: Request,
    response: Response,
):
    service = CaseExportService(
        request.app.state.engine,
        request.app.state.evidence_cipher,
        request.app.state.verifier_slots,
    )
    packet = execute(lambda: service.export(principal, case_id), "EXPORT")
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Disposition"] = f'attachment; filename="zecsolve-{case_id}.json"'
    return packet
