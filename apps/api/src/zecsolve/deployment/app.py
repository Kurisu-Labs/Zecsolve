from pathlib import PurePosixPath

from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles

from zecsolve.config import Settings
from zecsolve.deployment.settings import DeploymentSettings, application_settings
from zecsolve.main import create_app as workflow_app

RESERVED = {"api", "health", "docs", "redoc", "openapi.json"}
SECURITY_HEADERS = {
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "content-security-policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
        "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    ),
}


class WebApplication(StaticFiles):
    async def get_response(self, path, scope):
        parts = PurePosixPath(path).parts
        if any(part.startswith(".") for part in parts) or (parts and parts[0] in RESERVED):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            # Missing assets/API routes must not be disguised as a successful HTML page.
            accepts_html = any(
                key == b"accept" and b"text/html" in value for key, value in scope["headers"]
            )
            if error.status_code != 404 or not accepts_html or any("." in p for p in parts):
                raise
            return await super().get_response("index.html", scope)


class DeploymentBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def secure_send(message):
            if message["type"] == "http.response.start":
                headers = SECURITY_HEADERS.copy()
                if scope["scheme"] == "https":
                    headers["strict-transport-security"] = "max-age=31536000"
                existing = [
                    (k, v) for k, v in message["headers"] if k.decode().lower() not in headers
                ]
                message = {
                    **message,
                    "headers": existing
                    + [(key.encode(), value.encode()) for key, value in headers.items()],
                }
            await send(message)

        path = scope["path"]
        if (
            path == "/api/poc"
            or path.startswith("/api/poc/")
            or path.split("/")[1] in {"docs", "redoc", "openapi.json"}
        ):
            response = JSONResponse({"detail": "Not found"}, status_code=404)
            return await response(scope, receive, secure_send)
        if scope["scheme"] != "https" and path not in {"/health/live", "/health/ready"}:
            response = JSONResponse({"detail": "HTTPS required"}, status_code=400)
            return await response(scope, receive, secure_send)
        await self.app(scope, receive, secure_send)


def create_app(settings: Settings | None = None, deployment: DeploymentSettings | None = None):
    deployment = deployment or DeploymentSettings()
    if not (deployment.web_dist / "index.html").is_file():
        raise ValueError("Frontend build is missing")
    app = workflow_app(settings or application_settings(deployment))
    app.mount("/", WebApplication(directory=deployment.web_dist, html=True))
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[deployment.host], www_redirect=False)
    # Wrap the full FastAPI stack so even server errors receive privacy/security headers.
    return DeploymentBoundary(app)
