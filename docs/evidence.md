# Encrypted evidence submissions

This page describes the preserved merchant v1 contract. M4.4 adds explicit [customer/merchant evidence v2 submissions](customer-submissions.md), recorded sharing consent, scoped attribution, and minimal acknowledgements. Existing v1 requests, encrypted payloads and responses retain the behavior below; they do not gain reviewer-sharing consent retroactively.

Migration `0005` adds encrypted evidence bundles to merchant-owned cases. Receipt JSON and raw transaction hex are optional opaque UTF-8 strings: submission preserves exactly what was supplied, including whitespace, empty strings, and missing components. It does not verify receipts, decode transactions, trust source labels, or allocate credit.

## Configure the encryption key

Use a new 32-byte random key and a distinct nonsecret key ID for the initial setup. For example, in a private local shell:

```sh
export ZECSOLVE_EVIDENCE_KEY_ID=local-v1
export ZECSOLVE_EVIDENCE_KEY="$(python3 -c 'import base64,os; print(base64.b64encode(os.urandom(32)).decode())')"
make migrate
make api
```

Save that key securely before ending the shell. **Do not regenerate it on restart**: existing ciphertext needs the same key and ID. An ignored private `.env` or deployment secret store can provide these settings. Never put the key in Git, shared logs, or evidence metadata. Compose passes both variables to the API; no key is generated automatically.

This increment supports one configured key/ID at a time. Keep historical keys securely; changing the configured ID makes bundles written with another ID unavailable to the internal reader. Replacing the secret under the same ID causes authentication failure. Multi-key lookup, re-encryption, rotation tooling, retention, and purge APIs are not implemented here. Content and nonce reservations reject updates/deletes until a deliberate retention/rotation design preserves nonce safety.

Readiness requires a migrated database, executable verifier, and valid encryption configuration. `evidence_encryption_configured` reveals only a boolean. New uploads return 503 when encryption is unavailable; existing metadata and completed metadata-only retries can still be read by authorized merchants.

## Submit the public fixture

Create an invoice and case first. Set `MERCHANT_TOKEN` and `CASE_ID` locally, then run:

```sh
uv run --locked python - <<'PY'
import os
import uuid
from pathlib import Path
import httpx

headers = {
    "Authorization": "Bearer " + os.environ["MERCHANT_TOKEN"],
    "Idempotency-Key": str(uuid.uuid4()),
}
body = {
    "receipt_json": Path("fixtures/mainnet/receipt.json").read_bytes().decode("utf-8"),
    "raw_tx_hex": Path("fixtures/mainnet/transaction.hex").read_bytes().decode("utf-8"),
    "source": "bundled historical Glasspane fixture",
    "source_kind": "public_fixture",
    "processing_authorized": True,
    "share_with_reviewers": False,
}
path = f"/api/cases/{os.environ['CASE_ID']}/evidence"
with httpx.Client(base_url="http://127.0.0.1:8000") as client:
    created = client.post(path, json=body, headers=headers)
    assert created.status_code == 201, created.text
    replayed = client.post(path, json=body, headers=headers)
    assert replayed.status_code == 200 and replayed.json() == created.json()
    metadata = client.get(created.headers["location"], headers=headers)
    assert metadata.status_code == 200 and metadata.json() == created.json()
    print(metadata.json())
PY
```

Only metadata is returned. There is no public plaintext-download route. An internal `EvidenceService.read_content` method authorizes the merchant/case/evidence relationship before decryption and reauthorizes afterward; the [persisted-verification service](verification.md) now uses it before running the real verifier.

## Input, acknowledgement, and source meaning

- `receipt_json`: optional, at most 16,384 UTF-8 bytes. `raw_tx_hex`: optional, at most 4,000,002 UTF-8 bytes. JSON request and serialized bundle are capped at 4,200,000 bytes. Inputs are contents, never server file paths or fetch URLs.
- `source`: a nonempty label of at most 200 UTF-8 bytes; NUL is rejected. `source_kind` is `merchant_submission` by default or `public_fixture`. Both are caller assertions, not verified provenance, chain confirmation, or permission grants.
- `processing_authorized` must be the explicit boolean `true`. Disclosure version defaults to `evidence-disclosure-v1`. `share_with_reviewers` must remain `false`; reviewer sharing is not enabled by this increment.
- Acknowledgement text v1: “I am authorized to submit these selected payment details for processing in this merchant case. A receipt can disclose its selected amount, recipient, and memo, and copies already shared cannot be revoked. This submission does not authorize reviewer sharing or prove payment.”
- This records the authenticated **merchant's assertion**, credential ID, time, case, and evidence reference. It is not independently verified customer consent. Customer grants and the full consent/disclosure flow remain M4 work; use public fixtures for the current demo.

Unknown fields are rejected. The client cannot set the merchant, submitter, encryption key/nonce, storage reference, event, or case version. Malformed/tampered receipt content can be stored for a later verification attempt; storage success is not receipt validity.

## Encryption, hashes, and atomicity

The library [AES-GCM implementation](https://cryptography.io/en/stable/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM) uses a 256-bit key, fresh random 96-bit nonce, and full authentication tag. Associated data binds payload version, key ID, merchant ID, case ID, and evidence ID. The database stores key ID, nonce, and ciphertext; it never stores the key. A unique key-ID/nonce constraint and immutable content records preserve nonce reservations. A detected collision rolls back and returns a retryable 409.

The encrypted plaintext is the versioned request's canonical JSON, retaining the exact submitted receipt/raw-tx strings. `payload_sha256` hashes those serialized bytes. `receipt_sha256` and `raw_tx_hex_sha256` hash each original UTF-8 string independently; null means absent, while an empty string has its own hash. The raw-hex hash is **not** the hash of decoded transaction bytes, which belongs to verification.

Source/acknowledgement metadata, IDs, hashes, case state, and audit references remain outside application encryption. Invoice and derived payment fields also remain outside this encrypted blob. Encrypted database volumes/backups, access controls, and comprehensive retention rules are still needed before real customer onboarding.

Metadata, ciphertext, idempotency result, case version/state, and `EVIDENCE_SUBMITTED` event commit in one transaction. Encryption runs outside database locks under the shared two-slot per-process capacity. Writes lock invoice before case, refresh the locked case state/version, validate its existing event chain, and recheck credentials after waits. Each accepted submission increments case version and event sequence together.

For `OPEN`/`AWAITING_EVIDENCE`, missing or empty required components yield `AWAITING_EVIDENCE`; supplying both returns `OPEN` awaiting verification. `UNDER_REVIEW` remains unchanged. This does not claim the supplied bytes are valid. New submissions to terminal cases are rejected; a completed retry still returns its original metadata.

Keys are scoped to merchant + credential + case + submission operation. Same key/body returns 200 without new ciphertext/events; changed body returns 409. A new key intentionally records a new submission, even for identical content. Metadata carries the original submission's case version/state, which can differ from the case's current state.

## Access and migration boundaries

Unauthenticated/revoked/expired credentials return 401, foreign or unknown objects return 404, invalid input/key returns 422, oversized payloads return 413, busy crypto capacity returns 429, and key/database unavailability returns 503. Integrity failures and unavailable audit/legacy context return a controlled 409. Metadata responses never include receipt/raw-tx content, ciphertext, or keys and use `Cache-Control: no-store`.

Migration `0005` preserves existing evidence hashes/references without pretending old evidence is encrypted or inventing ownership metadata. Old records are not served as new encrypted bundles. New evidence metadata, content, and retry records reject ordinary edits/deletes. Downgrade serializes with creators and refuses to discard encrypted evidence. Database administrators can still alter those controls; the application does not claim protection from an administrator rewriting metadata or schema.

Published contracts: [request](../contracts/evidence-submit-request.schema.json), [stored metadata](../contracts/evidence-stored.schema.json), and [audit event](../contracts/evidence-submitted-event.schema.json). The [persisted verification and initial report](verification.md) are now implemented. Customer writes are covered by the v2 guide; reviewer projections, export, and purge/rotation remain subsequent work.
