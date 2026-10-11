import pytest
from pydantic import ValidationError


def test_customer_cannot_claim_reviewer_permissions():
    from zecsolve.schemas.access import GrantScopeV1

    assert GrantScopeV1(role="customer").report_sections == []
    for changes in (
        {"report_sections": ["invoice"]},
        {"allow_export": True},
        {"evidence_ids": ["00000000-0000-0000-0000-000000000001"]},
    ):
        with pytest.raises(ValidationError):
            GrantScopeV1(role="customer", **changes)
    with pytest.raises(ValidationError):
        GrantScopeV1(role="reviewer", report_sections=["secrets"])
    with pytest.raises(ValidationError):
        GrantScopeV1(role="reviewer", allow_export=1)
