import hmac
import threading
from contextlib import asynccontextmanager
from typing import Annotated

from alembic.script import ScriptDirectory
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from zecsolve import __version__
from zecsolve.adapters.address import AddressNormalizer
from zecsolve.adapters.chain import OfflineObserver, no_trusted_source
from zecsolve.adapters.evidence_crypto import EvidenceCipher
from zecsolve.adapters.rpc import ZebraObserver
from zecsolve.adapters.verifier import VerifierAdapter
from zecsolve.api.cases import router as case_router
from zecsolve.api.evidence import router as evidence_router
from zecsolve.api.grants import router as grant_router
from zecsolve.api.invoices import router as invoice_router
from zecsolve.api.observations import router as observation_router
from zecsolve.api.resolutions import router as resolution_router
from zecsolve.api.verifications import router as verification_router
from zecsolve.auth.credentials import MerchantPrincipal
from zecsolve.auth.dependencies import require_merchant
from zecsolve.config import Settings
from zecsolve.db.session import make_engine
from zecsolve.schemas.auth import MerchantIdentity
from zecsolve.schemas.verification import VerificationReport, VerifyRequest


class BodyLimit:
    """Bound the complete JSON body, including requests without Content-Length."""

    def __init__(self, app, limit=4_200_000):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        messages, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > self.limit:
                response = JSONResponse({"detail": "Request too large"}, status_code=413)
                return await response(scope, receive, send)
            messages.append(message)
            if not message.get("more_body", False):
                break
        iterator = iter(messages)

        async def replay():
            message = next(iterator, None)
            return message if message is not None else await receive()

        await self.app(scope, replay, send)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = make_engine(settings)
    verifier = VerifierAdapter(settings.verifier_path, settings.verifier_timeout_seconds)
    slots = threading.BoundedSemaphore(2)
    migration_head = ScriptDirectory(str(settings.migrations_path.resolve())).get_current_head()

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(title="zecsolve", version=__version__, lifespan=lifespan)
    app.state.engine = engine
    observer = ZebraObserver(settings) if settings.rpc_url.get_secret_value() else OfflineObserver()
    app.state.chain_observer = observer
    app.state.chain_authority = (
        observer.authorizes if isinstance(observer, ZebraObserver) else no_trusted_source
    )
    app.state.normalizer = AddressNormalizer(
        settings.verifier_path, settings.verifier_timeout_seconds
    )
    app.state.verifier_slots = slots
    app.state.verifier = verifier
    app.state.evidence_cipher = EvidenceCipher(settings.evidence_key_id, settings.evidence_key)
    app.include_router(invoice_router)
    app.include_router(grant_router)
    app.include_router(case_router)
    app.include_router(evidence_router)
    app.include_router(verification_router)
    app.include_router(resolution_router)
    app.include_router(observation_router)
    app.add_middleware(BodyLimit)
    bearer = HTTPBearer(auto_error=False)

    def require_poc_access(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ):
        token = settings.poc_token.get_secret_value()
        if not token:
            raise HTTPException(503, "POC access is disabled; configure ZECSOLVE_POC_TOKEN")
        if credentials is None or not hmac.compare_digest(
            credentials.credentials.encode(), token.encode()
        ):
            raise HTTPException(
                401, "Invalid POC credentials", headers={"WWW-Authenticate": "Bearer"}
            )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        # FastAPI's default errors can echo receipt/key-bearing request input.
        return JSONResponse(
            status_code=422, content={"detail": "Invalid request format or field size"}
        )

    @app.middleware("http")
    async def private_responses(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health/live")
    def live():
        return {"name": "zecsolve", "version": __version__, "status": "ok"}

    @app.get("/health/ready")
    def ready():
        database = False
        try:
            with engine.connect() as connection:
                database = tuple(
                    connection.scalars(text("SELECT version_num FROM alembic_version"))
                ) == (migration_head,)
        except SQLAlchemyError:
            pass
        checks = {
            "database_migrated": database,
            "verifier_available": verifier.available(),
            "evidence_encryption_configured": app.state.evidence_cipher.available,
        }
        return JSONResponse(status_code=200 if all(checks.values()) else 503, content=checks)

    @app.get("/api/auth/me", response_model=MerchantIdentity)
    def merchant_identity(principal: Annotated[MerchantPrincipal, Depends(require_merchant)]):
        return MerchantIdentity(
            merchant_id=principal.merchant_id, credential_id=principal.credential_id
        )

    @app.post(
        "/api/poc/verify",
        response_model=VerificationReport,
        dependencies=[Depends(require_poc_access)],
    )
    def verify(payload: VerifyRequest):
        if not slots.acquire(blocking=False):
            raise HTTPException(429, "Verifier busy; retry shortly")
        try:
            return verifier.verify(payload.receipt_json, payload.raw_tx_hex)
        finally:
            slots.release()

    return app


app = create_app()
