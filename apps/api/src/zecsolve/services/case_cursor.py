"""Bounded continuation positions, never authorization credentials."""

import base64
import binascii
import uuid
from typing import Literal

from pydantic import ValidationError

from zecsolve.domain.statuses import CaseState
from zecsolve.schemas.case import MAX_CASE_CURSOR_LENGTH
from zecsolve.schemas.verification import Contract
from zecsolve.services.workflow import WorkflowError


class CaseCursorV1(Contract):
    schema_version: Literal["1"]
    merchant_id: uuid.UUID
    case_id: uuid.UUID
    state: CaseState | None


def encode_case_cursor(merchant_id: uuid.UUID, case_id: uuid.UUID, state: CaseState | None) -> str:
    payload = CaseCursorV1(
        schema_version="1", merchant_id=merchant_id, case_id=case_id, state=state
    )
    return base64.urlsafe_b64encode(payload.model_dump_json().encode()).decode().rstrip("=")


def decode_case_cursor(token: str, merchant_id: uuid.UUID, state: CaseState | None) -> uuid.UUID:
    try:
        if not token or len(token) > MAX_CASE_CURSOR_LENGTH:
            raise ValueError("Invalid length")
        raw = base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
        if base64.urlsafe_b64encode(raw).decode().rstrip("=") != token:
            raise ValueError("Noncanonical encoding")
        position = CaseCursorV1.model_validate_json(raw)
        if position.merchant_id != merchant_id or position.state != state:
            raise ValueError("Cursor belongs to another listing")
    except (ValueError, binascii.Error, ValidationError):
        raise WorkflowError(422, "INVALID_CASE_CURSOR") from None
    # The caller must still authorize and look up this position within the merchant's cases.
    return position.case_id
