from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from zecsolve.auth.browser import session_from_request
from zecsolve.auth.credentials import MerchantPrincipal, authenticate_merchant, token_digest

merchant_bearer = HTTPBearer(auto_error=False, scheme_name="MerchantCredential")


def require_actor(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(merchant_bearer)],
):
    unauthorized = HTTPException(
        401, "Invalid merchant credentials", headers={"WWW-Authenticate": "Bearer"}
    )
    if credentials is None:
        if request.headers.get("authorization") is not None:
            raise unauthorized
        return session_from_request(request)[0]
    if token_digest(credentials.credentials) is None:
        raise unauthorized
    try:
        with Session(request.app.state.engine) as session:
            principal = authenticate_merchant(session, credentials.credentials)
    except SQLAlchemyError:
        raise HTTPException(503, "Merchant authentication unavailable") from None
    if principal is None:
        raise unauthorized
    return principal


def require_merchant(principal: Annotated[object, Depends(require_actor)]) -> MerchantPrincipal:
    if not isinstance(principal, MerchantPrincipal):
        raise HTTPException(403, "MERCHANT_REQUIRED")
    return principal
