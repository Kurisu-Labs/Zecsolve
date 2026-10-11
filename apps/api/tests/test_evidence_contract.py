import pytest
from pydantic import ValidationError


def test_evidence_preserves_missing_and_original_content_without_echoing_repr():
    from zecsolve.schemas.evidence import EvidenceSubmitRequest

    request = EvidenceSubmitRequest(
        receipt_json=' {"ock":"private-disclosure"}\n',
        raw_tx_hex=" AA00\n",
        source="public demo",
        source_kind="public_fixture",
        processing_authorized=True,
    )
    assert request.receipt_json == ' {"ock":"private-disclosure"}\n'
    assert request.raw_tx_hex == " AA00\n"
    assert "private-disclosure" not in repr(request)
    absent = EvidenceSubmitRequest(source="missing receipt", processing_authorized=True)
    assert absent.receipt_json is None and absent.raw_tx_hex is None
    assert absent.share_with_reviewers is False


@pytest.mark.parametrize(
    "extra",
    [
        {"receipt_json": "é" * 8193},
        {"raw_tx_hex": "a" * 4_000_003},
        {"receipt_json": "\ud800"},
        {"source": "bad\0label"},
        {"processing_authorized": False},
        {"processing_authorized": 1},
        {"share_with_reviewers": 0},
        {"share_with_reviewers": True},
        {"merchant_id": "forged"},
        {"key_id": "attacker"},
        {"storage_ref": "/etc/passwd"},
    ],
)
def test_evidence_rejects_oversized_invalid_or_privileged_input(extra):
    from zecsolve.schemas.evidence import EvidenceSubmitRequest

    with pytest.raises(ValidationError):
        EvidenceSubmitRequest.model_validate(
            {"source": "test", "processing_authorized": True, **extra}
        )
