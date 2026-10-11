import pytest
from test_verification_api import verification_api as verification_api

pytestmark = pytest.mark.postgres


def test_http_resolution_rejects_forged_confirmation_and_supports_noncredit_actions(
    verification_api,
):
    api, headers, case, evidence = verification_api
    attempt = api.post(
        f"/api/cases/{case}/verify", headers=headers, json={"evidence_id": evidence}
    ).json()
    request = dict(
        action="APPROVE_OUTPUT",
        verification_id=attempt["verification_id"],
        expected_case_version=3,
        reason="Reviewed",
    )
    path = f"/api/cases/{case}/resolve"
    assert (
        api.post(path, headers=headers, json=request | {"chain_state": "CONFIRMED"}).status_code
        == 422
    )
    blocked = api.post(path, headers=headers, json=request)
    assert blocked.status_code == 409 and blocked.json()["detail"]["code"] == "CREDIT_INELIGIBLE"
    request = dict(
        action="REQUEST_EVIDENCE", expected_case_version=3, reason="Need another receipt"
    )
    created = api.post(path, headers=headers, json=request)
    assert created.status_code == 201 and created.json()["case_state"] == "AWAITING_EVIDENCE"
    assert created.json()["allocated_zat"] == 0
    replay = api.post(path, headers=headers, json=request)
    assert replay.status_code == 200 and replay.json() == created.json()
    assert replay.headers["idempotency-replayed"] == "true"
    stale = api.post(path, headers=headers | {"Idempotency-Key": "stale"}, json=request)
    assert stale.status_code == 409 and stale.json()["detail"]["current_case_version"] == 4
    report = api.get(created.headers["location"], headers=headers)
    assert report.status_code == 200 and len(report.json()["decisions"]) == 1
    assert report.headers["cache-control"] == "no-store"
    assert api.post(path, json=request).status_code == 401
