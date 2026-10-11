from pathlib import Path

from pydantic import Field, SecretStr
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
