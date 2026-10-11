from pathlib import Path

from pydantic import Field, IPvAnyAddress
from pydantic_settings import BaseSettings, SettingsConfigDict

from zecsolve.config import Settings


class DeploymentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZECSOLVE_DEPLOY_", extra="ignore")
    host: str = Field(pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")
    web_dist: Path = Path("/app/web")
    secrets_dir: Path = Path("/run/secrets")
    proxy_ip: IPvAnyAddress = "172.30.7.2"


def application_settings(deployment: DeploymentSettings) -> Settings:
    return Settings(_env_file=None, _secrets_dir=deployment.secrets_dir)
