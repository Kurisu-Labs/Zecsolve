import logging.config
import subprocess
import sys

import uvicorn

from zecsolve.deployment.logging import LOGGING
from zecsolve.deployment.settings import DeploymentSettings, application_settings


def main():
    logging.config.dictConfig(LOGGING)
    try:
        from zecsolve.deployment.app import create_app

        deployment = DeploymentSettings()
        settings = application_settings(deployment)
        app = create_app(settings, deployment)
        # Alembic's own logging/tracebacks can contain connection/SQL details.
        # Keep migration output private and expose only a fixed failure event.
        migration = subprocess.run(
            [sys.executable, "-m", "zecsolve.deployment.migrate"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
            check=False,
        )
        if migration.returncode:
            raise RuntimeError("Migration failed")
    except Exception:
        logging.getLogger("uvicorn.error").error("Deployment startup failed")
        return 1
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=1,
        access_log=False,
        log_config=LOGGING,
        proxy_headers=True,
        forwarded_allow_ips=str(deployment.proxy_ip),
        limit_concurrency=32,
        timeout_keep_alive=5,
        timeout_graceful_shutdown=30,
        server_header=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
