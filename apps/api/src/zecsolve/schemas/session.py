import uuid
from datetime import UTC
from typing import Literal

from pydantic import AwareDatetime, Field, field_validator

from zecsolve.schemas.access import AccessContextV1
from zecsolve.schemas.verification import Contract


class SessionExchangeRequest(Contract):
    code: str = Field(
        pattern=r"^zs[mg]_[A-Za-z0-9_-]{43}$", min_length=47, max_length=47, repr=False
    )


class SessionInfoV1(Contract):
    schema_version: Literal["1"] = "1"
    session_id: uuid.UUID
    created_at: AwareDatetime
    expires_at: AwareDatetime
    access: AccessContextV1
    csrf_header: Literal["X-CSRF-Token"] = "X-CSRF-Token"
    csrf_cookie: Literal["__Host-zecsolve_csrf"] = "__Host-zecsolve_csrf"

    @field_validator("created_at", "expires_at")
    @classmethod
    def utc_times(cls, value):
        return value.astimezone(UTC)
