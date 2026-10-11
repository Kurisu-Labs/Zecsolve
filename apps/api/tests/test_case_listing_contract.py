import base64
import json
import uuid

import pytest
from pydantic import ValidationError
from zecsolve.domain.statuses import CaseState
from zecsolve.schemas.case import CaseListQuery, CaseListV1
from zecsolve.services.case_cursor import decode_case_cursor, encode_case_cursor
from zecsolve.services.workflow import WorkflowError


def test_listing_query_is_bounded_and_rejects_identity_or_unknown_filters():
    assert CaseListQuery().limit == 50
    for fields in (
        {"limit": 0},
        {"limit": 101},
        {"limit": "NaN"},
        {"state": "PAID"},
        {"cursor": ""},
        {"cursor": "a" * 513},
        {"cursor": "private+input"},
        {"merchant_id": str(uuid.uuid4())},
        {"offset": 1},
    ):
        with pytest.raises(ValidationError):
            CaseListQuery(**fields)
    for state in CaseState:
        assert CaseListQuery(state=state, limit=100).state == state


def test_cursor_binds_merchant_and_state_without_binding_one_credential():
    merchant, case = uuid.uuid4(), uuid.uuid4()
    for state in (None, *CaseState):
        token = encode_case_cursor(merchant, case, state)
        assert CaseListQuery(cursor=token).cursor == token
        assert decode_case_cursor(token, merchant, state) == case
        for other_merchant, other_state in (
            (uuid.uuid4(), state),
            (merchant, CaseState.OPEN if state is None else None),
        ):
            with pytest.raises(WorkflowError) as error:
                decode_case_cursor(token, other_merchant, other_state)
            assert (error.value.status, error.value.code) == (422, "INVALID_CASE_CURSOR")


@pytest.mark.parametrize(
    "payload",
    [b"not json", b"[]", b"null", b"\xff", b'{"schema_version":"2"}', b'{"unexpected":true}'],
)
def test_cursor_rejects_invalid_payload_without_echoing_it(payload):
    token = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    with pytest.raises(WorkflowError, match="^INVALID_CASE_CURSOR$"):
        decode_case_cursor(token, uuid.uuid4(), None)


@pytest.mark.parametrize("token", ["", "a" * 513, "a", "%%%%", "AA==", "AB", "é"])
def test_cursor_rejects_malformed_or_noncanonical_encoding(token):
    with pytest.raises(WorkflowError, match="^INVALID_CASE_CURSOR$"):
        decode_case_cursor(token, uuid.uuid4(), None)


def test_listing_schemas_match_published_contracts(root):
    for name, model in (("case-list-query", CaseListQuery), ("case-list", CaseListV1)):
        assert (
            json.loads((root / f"contracts/{name}.schema.json").read_text())
            == model.model_json_schema()
        )
