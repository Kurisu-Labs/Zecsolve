# Invoice snapshots

This M1 increment creates and retrieves merchant-owned invoices. It does not create a case, verify evidence, allocate credit, move funds, or establish chain confirmation.

## Create and read

Run `make migrate` (head `0003`) and `make api` from the repository root. Provision a merchant credential using the [operator CLI](../README.md#provision-merchant-identity). Put that credential in the local `MERCHANT_TOKEN` environment variable, then run this example with the existing public fixture:

```sh
uv run --locked python - <<'PY'
import json
import os
import uuid
from pathlib import Path
import httpx

manifest = json.loads(Path("fixtures/manifest.json").read_text())
body = {
    "expected_zat": 200_000,
    "network": "mainnet",
    "pool": "orchard",
    "receiver_address": manifest["expected"]["receiver_address"],
    "expected_memo": manifest["expected"]["memo_text"],
}
headers = {
    "Authorization": "Bearer " + os.environ["MERCHANT_TOKEN"],
    "Idempotency-Key": str(uuid.uuid4()),
}
with httpx.Client(base_url="http://127.0.0.1:8000") as client:
    created = client.post("/api/invoices", json=body, headers=headers)
    assert created.status_code == 201, created.text
    replayed = client.post("/api/invoices", json=body, headers=headers)
    assert replayed.status_code == 200 and replayed.json() == created.json()
    fetched = client.get(created.headers["location"], headers=headers)
    assert fetched.status_code == 200 and fetched.json() == created.json()
    print(json.dumps(created.json(), indent=2))
PY
```

## Inputs and policy

- `expected_zat`: strictly an integer from 1 through 2,100,000,000,000,000. Floats, booleans, and numeric strings are rejected.
- `network`: mainnet only. `pool`: Orchard or Sapling. `receiver_address`: at most 1,024 UTF-8 bytes, validated by the Rust normalizer for the requested network/pool.
- `expected_memo`: optional UTF-8 text, at most 512 bytes. Preserve the original text and right-pad its encoded bytes with zeroes to 512 bytes for matching. Null means no expected memo; an empty string is an explicit all-zero memo. NUL characters and unpaired surrogates are rejected as unsupported text.
- `expires_at`: optional timezone-aware ISO date/time, normalized to UTC. Numeric timestamps, including numeric strings, are rejected. A new invoice must not already be expired when its transaction checks the database clock. A completed retry can still return its original invoice after that invoice expires.
- Unknown fields are rejected. The caller cannot choose merchant identity, normalized receiver bytes, or policy settings.

The server persists policy version `invoice-policy-v1`, including the current rules version, ten required confirmations, a 60-second maximum observation age, exact memo binding, no overpayment approval, and `unique_receiver_binding=false`. These are stored defaults for later decision services; creation does not check the blockchain or imply credit eligibility. Missing memo binding cannot be bypassed by merely matching the amount or receiver.

## Retry and access rules

`Idempotency-Key` must contain 1–128 ASCII letters, digits, underscores, dots, colons, or hyphens. Use a fresh UUID for each intended creation, and retain it while retrying that creation.

Keys are scoped to merchant + credential + the create-invoice operation. Reuse with the same validated body returns the original safe snapshot (200 and `Idempotency-Replayed: true`); a different body returns 409. Equivalent UTC offsets and omitted versus explicit null optional fields normalize to the same request. The original address and memo text remain significant. A different key or credential represents a separate creation, even for identical invoice terms.

Authenticate before replay, then recheck current authorization in the short database transaction. Credential checks acquire a shared row lock before checking revocation and a fresh database clock, so credentials that expire while waiting cannot be used for reads or retries. Normalization runs outside all database transactions under the same per-process capacity limit as POC verification. Concurrent same-key creates commit only one invoice/policy/retry record; the losing transaction rolls back before reading the winner. All lock waits are bounded at five seconds.

| Status | Meaning |
|---|---|
| 201 | New invoice, policy, and retry record committed |
| 200 | Read or replay of the original snapshot |
| 401 | Missing, invalid, expired, or revoked merchant credential |
| 404 | Unknown or inaccessible invoice; no foreign merchant details disclosed |
| 409 | Key/body conflict, retryable database lock conflict, or legacy policy unavailable |
| 422 | Invalid input/key, invalid recipient, or already-expired new invoice |
| 429 | Shared verifier capacity is busy |
| 503 | Normalizer or database unavailable; internal database details are omitted |

## Snapshot hash and migration

The response contains `schema_version`, invoice/merchant/policy IDs, UTC `created_at`, `terms`, `policy`, and `snapshot_hash`. Version 1 hashes the response object **excluding `created_at` and `snapshot_hash`**. Serialization uses sorted string keys, compact separators, UTF-8 without ASCII escaping, JSON primitives without floats/NaN, and the UTC timestamps emitted by the contract. Memo/receiver bytes are lowercase hex. This is the project's versioned serialization profile, not a claim of universal JSON canonicalization.

The hash binds exact invoice terms, normalized receiver, padded memo, merchant/invoice/policy IDs, and policy configuration. It provides an integrity reference, not a signature or independent proof of merchant ownership. Request and response schemas are published in [contracts/](../contracts/); regenerate them with `make schema`.

Migration `0003` adds policy and creation-request tables, nullable historical fields, ownership constraints, and immutable triggers. Existing invoices retain their terms and hashes; their policy reference/version remain null. The new read route returns `LEGACY_INVOICE_POLICY_UNAVAILABLE` for those rows instead of inventing a policy. Invoice/policy/retry snapshots reject ordinary updates and deletes. A database administrator can still alter these controls.

There is no invoice-edit route. Corrections require a new snapshot. Downgrading past `0003` refuses to erase policy evidence when new invoices exist; use a forward migration for deployed data. Empty-schema upgrade/downgrade remains available for development tests.
