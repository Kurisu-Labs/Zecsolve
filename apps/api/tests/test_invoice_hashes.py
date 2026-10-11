import hashlib
import uuid
from datetime import UTC, datetime

import pytest
from zecsolve.schemas.address import NormalizedReceiver
from zecsolve.schemas.invoice import InvoiceCreateRequest, InvoicePolicyV1


def test_canonical_hash_has_stable_utf8_bytes_and_rejects_floats():
    from zecsolve.domain.snapshots import canonical_bytes, digest

    value = {"z": [1, False, None], "a": "é"}
    expected = b'{"a":"\xc3\xa9","z":[1,false,null]}'
    assert canonical_bytes(value) == expected
    assert digest(value) == hashlib.sha256(expected).hexdigest()
    for invalid in [{"amount": 1.0}, {"items": [float("nan")]}, {1: "key"}]:
        with pytest.raises(ValueError):
            canonical_bytes(invalid)


def test_snapshot_binds_exact_terms_owner_policy_and_receiver():
    from zecsolve.domain.snapshots import invoice_snapshot

    request = InvoiceCreateRequest(
        expected_zat=200_000,
        network="mainnet",
        pool="orchard",
        receiver_address="u1example",
        expected_memo="é",
        expires_at="2030-01-01T07:00:00+07:00",
    )
    receiver = NormalizedReceiver(network="mainnet", pool="orchard", receiver_hex="01" * 43)
    fields = dict(
        invoice_id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        created_at=datetime.now(UTC),
        request=request,
        receiver=receiver,
        policy=InvoicePolicyV1(),
    )
    snapshot = invoice_snapshot(**fields)
    assert snapshot.terms.memo_hex == (b"\xc3\xa9" + bytes(510)).hex()
    assert snapshot.terms.expected_memo == "é"
    same = request.model_copy(update={"expires_at": datetime(2030, 1, 1, tzinfo=UTC)})
    assert invoice_snapshot(**{**fields, "request": same}).snapshot_hash == snapshot.snapshot_hash
    for change in [
        {"merchant_id": uuid.uuid4()},
        {"policy_id": uuid.uuid4()},
        {"request": request.model_copy(update={"expected_zat": 1})},
        {"request": request.model_copy(update={"expected_memo": "other"})},
        {"receiver": receiver.model_copy(update={"receiver_hex": "02" * 43})},
        {"policy": InvoicePolicyV1(minimum_confirmations=20)},
    ]:
        assert invoice_snapshot(**{**fields, **change}).snapshot_hash != snapshot.snapshot_hash
    with pytest.raises(ValueError):
        invoice_snapshot(**{**fields, "receiver": receiver.model_copy(update={"pool": "sapling"})})
