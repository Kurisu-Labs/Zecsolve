import uuid
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from zecsolve.schemas.access import GrantScopeV1
from zecsolve.schemas.verification import Contract


class GrantCreateRequest(Contract):
    scope: GrantScopeV1
    ttl_hours: Annotated[int, Field(strict=True, ge=1, le=168)] = 24


class GrantMetadataV1(Contract):
    schema_version: Literal["1"] = "1"
    grant_id: uuid.UUID
    case_id: uuid.UUID
    merchant_id: uuid.UUID
    issued_by: uuid.UUID
    scope: GrantScopeV1
    created_at: AwareDatetime
    expires_at: AwareDatetime
    revoked_at: AwareDatetime | None


class GrantCreatedV1(Contract):
    grant: GrantMetadataV1
    access_code: Annotated[str, Field(pattern=r"^zsg_[A-Za-z0-9_-]{43}$")] | None = Field(
        default=None, repr=False
    )


class GrantListV1(Contract):
    schema_version: Literal["1"] = "1"
    items: list[GrantMetadataV1]
