import json
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from zecsolve.schemas.evidence import EvidenceSubmitRequest, EvidenceSubmitRequestV2
from zecsolve.schemas.submission import ClaimSubmitRequest, SubmissionAcknowledgementV1


def test_explicit_disclosure_is_required_and_legacy_evidence_stays_unchanged():
    legacy = EvidenceSubmitRequest(source="legacy", processing_authorized=True)
    assert legacy.disclosure_version == "evidence-disclosure-v1"
    with pytest.raises(ValidationError):
        EvidenceSubmitRequestV2(source="new", processing_authorized=True)
    request = EvidenceSubmitRequestV2(
        source="customer assertion",
        processing_authorized=True,
        disclosure_version="evidence-disclosure-v2",
        receipt_json=" \n{}\n",
        raw_tx_hex="",
    )
    assert not request.share_with_reviewers and request.claim_id is None
    assert request.receipt_json == " \n{}\n" and request.raw_tx_hex == ""
    with pytest.raises(ValidationError):
        EvidenceSubmitRequest(**{**legacy.model_dump(), "share_with_reviewers": True})


@pytest.mark.parametrize("field", ["processing_authorized", "share_with_reviewers"])
@pytest.mark.parametrize("value", [1, "true", None])
def test_claim_and_evidence_consent_requires_booleans(field, value):
    for model, body in (
        (
            ClaimSubmitRequest,
            {"note": "reported missing receipt", "disclosure_version": "claim-disclosure-v1"},
        ),
        (
            EvidenceSubmitRequestV2,
            {"source": "customer assertion", "disclosure_version": "evidence-disclosure-v2"},
        ),
    ):
        with pytest.raises(ValidationError):
            model.model_validate({**body, "processing_authorized": True, field: value})


@pytest.mark.parametrize(
    "extra",
    [
        {"note": " "},
        {"note": "é" * 2049},
        {"note": "bad\0note"},
        {"reported_txid": "https://example.test"},
        {"merchant_id": str(uuid.uuid4())},
        {"claimant_role": "merchant"},
        {"case_version": 1},
        {"processing_authorized": False},
    ],
)
def test_claim_bounds_and_server_owned_fields(extra):
    with pytest.raises(ValidationError):
        ClaimSubmitRequest.model_validate(
            {
                "note": "untrusted claim",
                "disclosure_version": "claim-disclosure-v1",
                "processing_authorized": True,
                **extra,
            }
        )


def test_claim_defaults_and_minimal_acknowledgement():
    claim = ClaimSubmitRequest(
        note="<b>untrusted text</b>",
        disclosure_version="claim-disclosure-v1",
        processing_authorized=True,
    )
    assert not claim.share_with_reviewers and claim.note not in repr(claim)
    ack = SubmissionAcknowledgementV1(
        operation="claim", submission_id=uuid.uuid4(), accepted_at=datetime.now(UTC)
    )
    assert set(json.loads(ack.model_dump_json())) == {
        "schema_version",
        "status",
        "operation",
        "submission_id",
        "accepted_at",
    }
