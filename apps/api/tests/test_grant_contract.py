import pytest
from pydantic import ValidationError


def test_grant_lifetime_and_scope_are_bounded():
    from zecsolve.schemas.grant import GrantCreateRequest

    assert GrantCreateRequest(scope={"role": "customer"}).ttl_hours == 24
    for ttl in (0, 169, True, 1.2):
        with pytest.raises(ValidationError):
            GrantCreateRequest(scope={"role": "customer"}, ttl_hours=ttl)
    with pytest.raises(ValidationError):
        GrantCreateRequest(scope={"role": "merchant"})
