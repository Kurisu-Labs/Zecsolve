import pytest
from test_verification_api import verification_api as verification_api

pytestmark = pytest.mark.postgres


def test_grant_api_secret_disclosure_replay_metadata_and_revocation(verification_api):
    api, headers, case, _ = verification_api
    path = f"/api/cases/{case}/grants"
    body = {"scope": {"role": "customer"}}
    created = api.post(path, headers=headers, json=body)
    assert created.status_code == 201
    code = created.json()["access_code"]
    grant_id = created.json()["grant"]["grant_id"]
    replay = api.post(path, headers=headers, json=body)
    assert replay.status_code == 200 and replay.json()["access_code"] is None
    listing = api.get(path, headers=headers)
    assert listing.status_code == 200 and code not in listing.text
    assert listing.headers["cache-control"] == "no-store"
    assert api.get(path).status_code == 401
    assert api.get(path, headers={"Authorization": "Bearer " + code}).status_code == 401
    revoked = api.delete(path + "/" + grant_id, headers=headers)
    assert revoked.status_code == 200 and revoked.json()["revoked_at"]
    assert api.delete(path + "/" + grant_id, headers=headers).json() == revoked.json()
