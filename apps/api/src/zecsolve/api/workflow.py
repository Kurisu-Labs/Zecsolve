from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from zecsolve.services.workflow import WorkflowError


def execute(operation, resource: str):
    try:
        return operation()
    except WorkflowError as error:
        headers = {"WWW-Authenticate": "Bearer"} if error.status == 401 else None
        raise HTTPException(error.status, error.code, headers=headers) from None
    except SQLAlchemyError as error:
        if getattr(getattr(error, "orig", None), "sqlstate", None) in ("55P03", "40P01", "40001"):
            raise HTTPException(409, f"RETRY_{resource}_OPERATION") from None
        raise HTTPException(503, f"{resource}_SERVICE_UNAVAILABLE") from None
