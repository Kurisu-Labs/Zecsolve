"""Version-1 project serialization: sorted keys, compact UTF-8 JSON, no floats."""

import hashlib
import json
import uuid
from datetime import datetime

from zecsolve.schemas.address import NormalizedReceiver
from zecsolve.schemas.invoice import (
    InvoiceCreateRequest,
    InvoicePolicyV1,
    InvoiceSnapshotV1,
    InvoiceTermsV1,
)


def canonical_bytes(value) -> bytes:
    def validate(item):
        if item is None or type(item) in (str, int, bool):
            return
        if type(item) is list:
            for child in item:
                validate(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                validate(child)
            return
        raise ValueError("Snapshot JSON must use string keys and contain no floats")

    validate(value)
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def invoice_snapshot(
    *,
    invoice_id: uuid.UUID,
    merchant_id: uuid.UUID,
    policy_id: uuid.UUID,
    created_at: datetime,
    request: InvoiceCreateRequest,
    receiver: NormalizedReceiver,
    policy: InvoicePolicyV1,
) -> InvoiceSnapshotV1:
    if (receiver.network, receiver.pool) != (request.network, request.pool):
        raise ValueError("Normalized receiver does not match requested network and pool")
    terms = InvoiceTermsV1(
        **request.model_dump(),
        receiver_hex=receiver.receiver_hex,
        memo_hex=request.memo_bytes.hex() if request.memo_bytes is not None else None,
    )
    # Creation time is response metadata, not a payment term or part of this hash.
    payload = {
        "schema_version": "1",
        "invoice_id": str(invoice_id),
        "merchant_id": str(merchant_id),
        "policy_id": str(policy_id),
        "terms": terms.model_dump(mode="json"),
        "policy": policy.model_dump(mode="json"),
    }
    return InvoiceSnapshotV1(**payload, created_at=created_at, snapshot_hash=digest(payload))
