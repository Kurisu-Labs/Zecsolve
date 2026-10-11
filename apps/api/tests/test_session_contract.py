import pytest
from pydantic import ValidationError


def test_session_exchange_accepts_only_initial_codes_and_redacts_repr():
    from zecsolve.schemas.session import SessionExchangeRequest

    code = "zsm_" + "a" * 43
    assert code not in repr(SessionExchangeRequest(code=code))
    for body in (
        {"code": "invalid"},
        {"code": "zss_" + "a" * 43},
        {"code": code, "role": "merchant"},
    ):
        with pytest.raises(ValidationError):
            SessionExchangeRequest(**body)


def test_browser_origins_require_exact_https_origins():
    from zecsolve.config import Settings

    for value in (
        "*",
        "http://example.com",
        "https://example.com/path",
        "https://user:pass@example.com",
        "null",
    ):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, browser_origins=[value])
    assert Settings(_env_file=None, browser_origins=["https://app.example"]).browser_origins == [
        "https://app.example"
    ]
