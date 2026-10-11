# Persisted verification and initial offline reports

Migration `0006` connects an owned encrypted evidence bundle to the real Rust verifier and an initial merchant report. Apply `make migrate` to the current head, configure the retained evidence key, and build the verifier with `make build`. Create an [invoice](invoices.md), [case](cases.md), and [evidence submission](evidence.md) first.

## Verify and read

Set `MERCHANT_TOKEN`, `CASE_ID`, and the submission's `EVIDENCE_ID` in your private shell:

```sh
uv run --locked python - <<'PY'
import os
import uuid
import httpx

headers = {
    "Authorization": "Bearer " + os.environ["MERCHANT_TOKEN"],
    "Idempotency-Key": str(uuid.uuid4()),
}
path = f"/api/cases/{os.environ['CASE_ID']}"
body = {"evidence_id": os.environ["EVIDENCE_ID"]}
with httpx.Client(base_url="http://127.0.0.1:8000") as client:
    attempt = client.post(path + "/verify", headers=headers, json=body)
    assert attempt.status_code == 201, attempt.text
    replay = client.post(path + "/verify", headers=headers, json=body)
    assert replay.status_code == 200 and replay.json() == attempt.json()
    report = client.get(attempt.headers["location"], headers=headers)
    assert report.status_code == 200, report.text
    print(report.json())
PY
```

The only request field is `evidence_id`. Merchant, actor, result, observation, rules inputs, evaluation, event, and case version/state are server-derived. A new attempt returns 201; the same merchant/credential/case/key/body returns the original attempt with 200 and `Idempotency-Replayed: true`. Changed evidence under the same key returns 409. A new key intentionally creates a new attempt. Keys follow the existing 1–128 ASCII letter/digit/underscore/dot/colon/hyphen format and are scoped independently of evidence submission.

`Location` selects this attempt in `GET /api/cases/{case_id}/report?verification_id=...`. Without that query, the report selects the latest persisted attempt. Selection must belong to the same owned case. The older `GET /api/cases/{id}` remains the current case summary plus opening event; its contract is unchanged.

## What is recorded

Authorized decryption and bounded Rust execution happen outside database transactions. The persistence transaction locks invoice then refreshed case, rechecks authorization and existing audit history, and commits all of these together:

- Validated verifier result and evidence/case/merchant/actor references.
- An explicit `UNAVAILABLE` chain observation with source `offline`, reason `NO_CHAIN_OBSERVER`, and null confirmation/block fields. Transaction identifiers/hashes are copied only when present in the result.
- Immutable invoice/policy and verification inputs, owned approved allocations, a foreign-output-conflict boolean, rules result, and snapshot hash.
- The `VERIFICATION_RECORDED` event, scoped retry record, and incremented case version/state.

The event binds result/evaluation hashes and references, without copying receipt, recovered memo, or receiver into its payload. Verification retries validate stored references, snapshot hash, result metadata, and event payload/header hashes. Reports also validate the complete known audit chain.

Completed domain results are persisted, including `NONE`, `INVALID`, `UNSUPPORTED`, `UNAVAILABLE`, and `ERROR`. Missing receipt is not invalid receipt; missing raw transaction/binary is unavailable; process, protocol, and temporary-storage failures are errors. New `VALID` or `INVALID` results move the case to `UNDER_REVIEW`; `NONE` moves it to `AWAITING_EVIDENCE`; technical/unsupported outcomes preserve its current state. Terminal cases reject new attempts, while completed retries remain readable.

Failed commits leave no partial attempt, observation, evaluation, event, retry record, or state change. Concurrent equal keys return one committed attempt, although concurrent callers can perform redundant verifier work before the short persistence transaction resolves the race.

## Report and balance meaning

`CaseReportV1` has `report_scope=INITIAL_OFFLINE` and `disclosure_scope=MERCHANT`. It contains the owned case, immutable invoice/policy, evidence metadata, attempts, observations, evaluation history, stored claim/resolution assertions, audit events, selected verification, and current balances. No claim/resolution creation route is added here, and an assertion is not independently established payment evidence.

The report reads one repeatable-read database snapshot. Its current balances use authoritative approved allocation rows, while past evaluation snapshots retain their original inputs and results. It projects only the latest or explicitly selected candidate; repeated verification attempts are never summed as unapproved payments. A case with no attempt has empty verification history and honest current balances. Foreign allocation conflicts do not disclose foreign invoice IDs or amounts.

With the bundled 100,000-zatoshi fixture and a matching 200,000-zatoshi invoice/memo, the offline report shows 0 credited, 200,000 outstanding, 100,000 candidate, and 100,000 projected outstanding. `eligible_for_credit` is always false. Receipt recovery, chain confirmation, and merchant approval remain separate facts; neither route writes an allocation or moves funds.

This increment supports stored rules version `0.1.0`. Unsupported versions fail closed. Trusted live observations, policy-aware confirmation approval, stale-decision checks, atomic merchant resolution, and replayable exports remain later work.

## Access, disclosure, and migration

Absent/revoked/expired credentials return 401; foreign or unknown IDs return 404; invalid input/key returns 422; occupied verifier capacity returns 429 before an attempt is recorded. Database/key availability failures return a generic 503. Ciphertext integrity, unsupported history/rules, retry-key conflicts, or retryable lock conflicts return controlled 409 errors. A concurrent credential update can also require retrying the report transaction. Encryption failures do not become accusations that the receipt is invalid. Responses use `Cache-Control: no-store`.

Reports and retries read stored results without decrypting the original bundle. They exclude original receipt/raw-tx strings, OCKs, ciphertext, and keys, but **do expose recovered memo, receiver, and amount to the owning merchant**. These derived fields and evaluation inputs are stored outside application encryption. The original evidence body remains AES-GCM encrypted. Keep database/backups/access controls and the deferred consent/retention work in scope before real customer use; current demonstrations use public fixtures.

Migration `0006` preserves legacy verification/observation rows without inventing ownership, policy, or chain provenance. Unsupported legacy workflow history is not presented as a new report. Scoped foreign keys and immutable observation/evaluation/retry records complement existing immutable attempts/events. Downgrade first serializes with authorization and workflow writers, then refuses to remove populated new verification history. Use forward migrations for deployed evidence and stop traffic before planned rollback. Hashes and triggers do not protect against an administrator rewriting data and controls.

Published schemas: [verify request](../contracts/case-verify-request.schema.json), [attempt](../contracts/verification-attempt.schema.json), and [initial offline report](../contracts/case-report.schema.json). This report is not a customer/reviewer grant, full consent flow, or replay packet.
