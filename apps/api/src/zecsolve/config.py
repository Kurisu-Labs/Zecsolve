from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZECSOLVE_", env_file=".env", extra="ignore")

    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://zecsolve:zecsolve@127.0.0.1:54329/zecsolve"
    )
    poc_token: SecretStr = SecretStr("")
    migrations_path: Path = Path("apps/api/migrations")
    verifier_path: Path = Path("target/debug/zecsolve-verifier")
    verifier_timeout_seconds: float = Field(default=10, gt=0, le=60)
    evidence_key_id: str = ""
    evidence_key: SecretStr = SecretStr("")
    rpc_url: SecretStr = SecretStr("")
    rpc_source_id: str = Field(default="trusted-zebra", pattern=r"^[a-zA-Z0-9_.-]{1,80}$")
    rpc_username: SecretStr = SecretStr("")
    rpc_password: SecretStr = SecretStr("")
    rpc_allow_private_http: bool = False
    rpc_timeout_seconds: float = Field(default=10, gt=0, le=30)
    rpc_tip_max_age_seconds: int = Field(default=900, ge=75, le=3600)

    browser_origins: list[str] = Field(default_factory=list)

    @field_validator("browser_origins")
    @classmethod
    def exact_https_origins(cls, values):
        for value in values:
            parsed = urlsplit(value)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
                or "*" in value
                or any(c.isspace() for c in value)
            ):
                raise ValueError("Browser origins must be exact HTTPS origins without paths")
            _ = parsed.port
        return values
