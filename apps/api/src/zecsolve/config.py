from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZECSOLVE_", env_file=".env", extra="ignore")

    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://zecsolve:zecsolve@127.0.0.1:54329/zecsolve"
    )
    poc_token: SecretStr = SecretStr("")
    verifier_path: Path = Path("target/debug/zecsolve-verifier")
    verifier_timeout_seconds: float = Field(default=10, gt=0, le=60)
