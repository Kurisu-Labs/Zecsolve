from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from zecsolve.api.workflow import execute
from zecsolve.auth.browser import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    require_browser_origin,
    session_from_request,
)
from zecsolve.schemas.session import SessionExchangeRequest, SessionInfoV1
from zecsolve.services.sessions import SessionService

router = APIRouter(prefix="/api/session", tags=["session"])


@router.post("", response_model=SessionInfoV1, status_code=201)
def exchange_session(payload: SessionExchangeRequest, request: Request):
    require_browser_origin(request)
    issued = execute(
        lambda: SessionService(request.app.state.engine).exchange(payload.code), "SESSION"
    )
    response = JSONResponse(status_code=201, content=issued.info.model_dump(mode="json"))
    age = int((issued.info.expires_at - issued.info.created_at).total_seconds())
    for name, value, http_only in (
        (SESSION_COOKIE, issued.token, True),
        (CSRF_COOKIE, issued.csrf_token, False),
    ):
        response.set_cookie(
            name,
            value,
            max_age=age,
            expires=issued.info.expires_at,
            path="/",
            secure=True,
            httponly=http_only,
            samesite="strict",
        )
    return response


@router.get("", response_model=SessionInfoV1)
def current_session(request: Request):
    return session_from_request(request)[1]


@router.delete("", status_code=204)
def logout_session(request: Request):
    session_from_request(request)
    execute(
        lambda: SessionService(request.app.state.engine).logout(request.cookies[SESSION_COOKIE]),
        "SESSION",
    )
    response = Response(status_code=204)
    for name, http_only in ((SESSION_COOKIE, True), (CSRF_COOKIE, False)):
        response.delete_cookie(name, path="/", secure=True, httponly=http_only, samesite="strict")
    return response
