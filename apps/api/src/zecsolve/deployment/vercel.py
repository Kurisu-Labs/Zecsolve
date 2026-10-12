"""Entrypoint for Vercel's private, platform-routed container runtime."""

import logging.config
import os

import uvicorn
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import make_url

from zecsolve.config import Settings
from zecsolve.db.session import make_engine
from zecsolve.deployment.app import create_app
from zecsolve.deployment.logging import LOGGING
from zecsolve.deployment.settings import DeploymentSettings


def runtime_configuration():
    # This entrypoint must not be used for a directly exposed Docker/VPS listener.
    # Vercel exclusively routes inbound traffic through its managed HTTP proxy.
    if os.getenv("VERCEL") != "1" or os.getenv("VERCEL_ENV") not in {"preview", "production"}:
        raise ValueError("Vercel runtime required")
    deployment = DeploymentSettings()
    settings = Settings(_env_file=None)
    url = make_url(settings.database_url.get_secret_value())
    if url.drivername != "postgresql+psycopg" or url.query.get("sslmode") != "verify-full":
        raise ValueError("Certificate-verified PostgreSQL connection required")
    if settings.browser_origins != [f"https://{deployment.host}"]:
        raise ValueError("One exact browser origin matching the deployment host is required")
    if not settings.evidence_key_id or not settings.evidence_key.get_secret_value():
        raise ValueError("Evidence encryption configuration required")
    if not settings.rpc_url.get_secret_value() or settings.rpc_allow_private_http:
        raise ValueError("Public HTTPS RPC configuration required")
    port = int(os.getenv("PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("Invalid server port")
    return settings, deployment, port


def require_current_schema(settings):
    """Migrations are an operator release step, never an autoscaling side effect."""
    head = ScriptDirectory(str(settings.migrations_path.resolve())).get_current_head()
    engine = make_engine(settings)
    try:
        with engine.connect() as connection:
            current = tuple(connection.scalars(text("SELECT version_num FROM alembic_version")))
        if current != (head,):
            raise ValueError("Apply release migrations before starting the application")
    finally:
        engine.dispose()


def main():
    logging.config.dictConfig(LOGGING)
    try:
        settings, deployment, port = runtime_configuration()
        require_current_schema(settings)
        app = create_app(settings, deployment)
    except Exception:
        logging.getLogger("uvicorn.error").error("Deployment startup failed")
        return 1
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        workers=1,
        access_log=False,
        log_config=LOGGING,
        proxy_headers=True,
        # Only the Vercel entrypoint trusts the platform-managed ingress. Compose
        # retains its single fixed proxy IP. Host, HTTPS, Origin and CSRF checks
        # remain enforced by the application behind this transport adapter.
        forwarded_allow_ips="*",
        limit_concurrency=32,
        timeout_keep_alive=5,
        timeout_graceful_shutdown=25,
        server_header=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
