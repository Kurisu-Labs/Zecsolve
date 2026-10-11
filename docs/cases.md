# Case opening and audit records

This increment opens a merchant-owned case from an existing supported invoice snapshot. It persists one `CASE_OPENED` event and a scoped retry record in the same transaction. It does not submit claims, upload evidence, verify payments, allocate credit, or produce the complete `CaseReportV1` planned for the workflow.

## Open and read

Run `make migrate` to the current head and `make api` from the repository root; case opening requires revision `0004` or later. Use a merchant credential and an invoice created through the [invoice API](invoices.md). Set local environment variables `MERCHANT_TOKEN` and `INVOICE_ID`, then run:

```sh
uv run --locked python - <<'PY'
import os
import uuid
import httpx

headers = {
    "Authorization": "Bearer " + os.environ["MERCHANT_TOKEN"],
    "Idempotency-Key": str(uuid.uuid4()),
}
body = {"invoice_id": os.environ["INVOICE_ID"]}
with httpx.Client(base_url="http://127.0.0.1:8000") as client:
    opened = client.post("/api/cases", headers=headers, json=body)
    assert opened.status_code in (200, 201), opened.text
    retried = client.post("/api/cases", headers=headers, json=body)
    assert retried.status_code == 200 and retried.json() == opened.json()
    current = client.get(opened.headers["location"], headers=headers)
    assert current.status_code == 200, current.text
    print(current.json())
PY
```

The only creation field is `invoice_id`. Merchant, actor, state, version, payload, and event identity are derived by the server. Unknown fields are rejected. A supported invoice has a version-1 snapshot and stored `invoice-policy-v1` policy; no policy is inferred for historical invoices. An expired invoice can still need a payment exception case, so opening a case does not itself impose a new invoice-expiry rule.

## Retry and current state

- New case: 201, `OPEN`, version 1, and the opening event. `Location` points to `GET /api/cases/{id}`.
- Reusing the same merchant/credential/key and invoice returns 200 and the original `CaseOpenedV1` outcome. Reusing that key with a different invoice returns 409.
- A new key, or another active credential of the same merchant, requesting the same invoice returns the existing case with 200. Its key is bound to that invoice, and no new case/event is created. The original opening actor is preserved.
- Creation retries always describe the original opening (`OPEN`, version 1), even if later workflow operations change the case. GET returns `CaseDetailV1` with the current state/version and the unchanged opening event. This increment exposes no state-transition route.
- Keys are scoped to the create-case operation, independently of invoice creation. Their allowed syntax is the same 1–128 ASCII letters, digits, underscores, dots, colons, and hyphens used by invoices. `Idempotency-Replayed: true` means an existing opening outcome was returned.

Creation authenticates first, locks the owned invoice before any existing case, then rechecks credential validity after lock waits. Duplicate requests serialize on that invoice. Cross-invoice key collisions roll back the losing case, event, and retry record before returning a conflict. Failed commits leave none of those records behind. Lock waits remain bounded at five seconds, and reads/replays recheck credential expiry and revocation.

Inaccessible invoice/case IDs return 404; credentials that are absent, revoked, or expired return 401. Bad fields or missing/invalid keys return 422. Legacy history, key conflicts, or retryable lock conflicts return 409. Database failures return a generic 503 without internal details. Responses use `Cache-Control: no-store`.

## Opening-event evidence

The persisted event contains:

- Schema version 1, event/case IDs, sequence 1, `CASE_OPENED`, server-derived `credential:<UUID>` actor, and UTC time.
- A payload containing only `invoice_id`, `invoice_snapshot_hash`, and `policy_id`. No receipt, memo, receiver, token, or foreign-case details are copied into it.
- `payload_hash`: SHA-256 of the payload under the [invoice serialization profile](invoices.md#snapshot-hash-and-migration).
- `previous_hash=null` for the first event.
- `event_hash`: SHA-256 of `schema_version`, `case_id`, `sequence`, `actor`, `action`, `at`, `payload_hash`, and `previous_hash`. Exclude `event_id`, raw `payload`, and `event_hash` from that header hash.

The read/replay service checks the stored payload/header hashes and invoice reference before returning the event. Ordinary updates/deletes of events and completed retry records are rejected. Hashes provide integrity references; they are not signatures, external notarization, or protection against an administrator rewriting data and controls. Only the initial event is written here; later event sequencing and state transitions belong to subsequent services.

## Historical rows and migration

Migration `0004` locks the case table while checking for duplicate invoice cases. If it finds duplicates, it stops with up to ten invoice IDs/counts for remediation and changes no rows. Do not silently remove or merge existing cases to make the migration pass.

Existing cases retain null `workflow_version`; existing event payload/schema fields stay null, while original hashes remain unchanged. Creation/read refuses unsupported historical workflow records instead of fabricating missing audit data.

Downgrade first takes exclusive locks in creation-request → case → event order. This waits for active creators before inspecting history. It refuses to remove any new case/event evidence; use forward migrations for deployed data. Empty-schema rollback remains available for development tests. Stop application traffic before any planned schema rollback.

Published schemas: [case creation](../contracts/case-create-request.schema.json), [opening outcome](../contracts/case-opened.schema.json), and [case detail](../contracts/case-detail.schema.json). [Encrypted merchant evidence submission](evidence.md) is now a separate implemented increment. An [initial offline verification report](verification.md) is also available on its own route. A case list, claims/decisions write services, and customer/reviewer projections remain pending.
