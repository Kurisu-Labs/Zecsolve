"""Cookie transport and CSRF checks; bearer authentication remains independent."""

import hmac

from fastapi import HTTPException, Request

from zecsolve.api.workflow import execute
from zecsolve.services.sessions import SessionService, secret_digest

SESSION_COOKIE = "__Host-zecsolve_session"
CSRF_COOKIE = "__Host-zecsolve_csrf"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def require_browser_origin(request: Request):
    origins = request.app.state.browser_origins
    if not origins:
        raise HTTPException(503, "BROWSER_SESSIONS_NOT_CONFIGURED")
    if request.url.scheme != "https":
        raise HTTPException(400, "SESSION_REQUIRES_HTTPS")
    if request.headers.get("origin") not in origins:
        raise HTTPException(403, "UNTRUSTED_ORIGIN")


def session_from_request(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(401, "INVALID_SESSION")
    if request.url.scheme != "https":
        raise HTTPException(400, "SESSION_REQUIRES_HTTPS")
    if request.method not in SAFE_METHODS:
        require_browser_origin(request)
    principal, info, csrf_hash = execute(
        lambda: SessionService(request.app.state.engine).authenticate(token), "SESSION"
    )
    if request.method not in SAFE_METHODS:
        csrf_header = request.headers.get(CSRF_HEADER, "")
        csrf_cookie = request.cookies.get(CSRF_COOKIE, "")
        hashed = secret_digest(csrf_header, "zsc")
        if (
            hashed is None
            or secret_digest(csrf_cookie, "zsc") is None
            or not hmac.compare_digest(hashed, csrf_hash)
            or not hmac.compare_digest(csrf_header, csrf_cookie)
        ):
            raise HTTPException(403, "INVALID_CSRF_TOKEN")
    return principal, info
