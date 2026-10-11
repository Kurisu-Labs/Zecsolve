from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from zecsolve.deployment.settings import DeploymentSettings, application_settings


def main():
    settings = application_settings(DeploymentSettings())
    config = Config("alembic.ini")
    engine = create_engine(
        settings.database_url.get_secret_value(), connect_args={"connect_timeout": 3}
    )
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
