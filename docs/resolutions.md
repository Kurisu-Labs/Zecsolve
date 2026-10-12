# Merchant decisions and atomic output allocation

Migration `0007` adds merchant decisions over the [persisted verification workflow](verification.md). Run `make migrate` to the current head before starting the API. `POST /api/cases/{case_id}/resolve` requires an active merchant credential, an `Idempotency-Key`, a reason, and the case version the merchant reviewed.

The deployed app defaults to an offline observer and default-deny source policy. A server-configured [trusted Zebra observer](chain.md) can authorize fresh RPC observations; **live-node validation and a fresh merchant approval trace merged in PR #27**; see the [recorded run](chain.md#recorded-live-run). Noncredit decisions are usable now. The isolated demo below exercises allocation with explicitly simulated confirmations; no public request field or environment toggle enables them in the app.

## Request and actions

Example request using the version from the latest case report:

```json
{
  "action": "REQUEST_EVIDENCE",
  "expected_case_version": 3,
  "reason": "Please provide the receipt for the remaining payment."
}
```

| Action | Verification reference | Effect |
|---|---|---|
| `APPROVE_OUTPUT` | Required, from this case | Allocate the entire recovered output only after policy checks; partial balance leaves `UNDER_REVIEW`, full coverage becomes `RESOLVED` |
| `REQUEST_EVIDENCE` | Must be absent/null | Move to `AWAITING_EVIDENCE`; no credit |
| `REJECT_EVIDENCE` | Required, from this case | Record merchant rejection and leave `UNDER_REVIEW`; no credit and no alteration of the cryptographic result |
| `CLOSE_UNRESOLVED` | Must be absent/null | Move to `CLOSED_UNRESOLVED`; preserve existing allocations and balances |

Approval/rejection adds `verification_id` to the JSON above. Reasons must contain non-whitespace text, contain no NUL, and fit within 2,000 UTF-8 bytes. Versions are positive integers, never booleans. Amount, output identity, receiver, actor, merchant, chain state, and trust flags are server-derived; unknown fields are rejected.

New decisions return 201 with a `ResolutionOutcomeV1`; completed replay returns 200 with `Idempotency-Replayed: true`. `Location` points to the case report. The outcome preserves the original actor/time, reason, post-decision state/version, allocated output/amount, decision evaluation, and post-decision balances. These captured balances may differ from a later report's current balance.

## Approval policy and transaction

Each new approval refreshes its observation outside database locks, and stores that immutable diagnostic even if approval is subsequently blocked. Refresh failure cannot reuse an earlier successful observation. The default observation is `UNAVAILABLE / NO_CHAIN_OBSERVER`; adapter errors become `UNAVAILABLE / OBSERVER_FAILED`. A source label alone grants no trust.

The decision evaluator is version `0.2.0`. It composes the preserved `0.1.0` invoice-binding/balance rules with stored policy thresholds and an explicit evaluation time. Existing immutable invoice policies and initial evaluations keep their original `0.1.0` selector and hashes; unsupported selectors fail closed. The default policy requires ten confirmations and an observation at most 60 seconds old. Future timestamps, insufficient confirmations, unauthorized sources, wrong network/txid/raw-byte hash, missing memo binding, recipient mismatch, zero-value output, duplicate allocation, and projected overpayment block approval. A source may report `CONFIRMED` but still fail the count, trust, or age requirement.

After refresh, the service locks invoice then case, reauthorizes the merchant, checks semantic replay, and compares the reviewed version. It calculates against current approved allocations and rechecks observation age after any lock wait. It commits decision evaluation, resolution, full-output allocation, case state/version, audit event, and retry record together. Noncredit decisions use the same transaction without creating an allocation. No operation moves ZEC, executes a refund, splits an output, reverses credit, or reassigns an allocation.

Different outputs on one invoice serialize through its invoice lock. A second concurrent decision must review the updated version/balance before resubmission. The allocation primary key protects the full `network:pool:txid:output_index` across invoices. A uniqueness-race loser rolls back its entire decision, then returns the winning same-invoice outcome or an opaque foreign conflict.

## Retry and failure semantics

Keys are scoped to merchant + credential + case + resolution operation, with the same 1–128 ASCII letter/digit/underscore/dot/colon/hyphen syntax as other writes. Same key/body returns the original decision; changed body returns 409. A new key for an already allocated output on the same invoice returns its original resolution without a new decision/event/credit and binds that new key. It does not replace the original reason or actor. Semantic and completed-key retries precede version/terminal checks, require current authorization, and do not refresh chain evidence.

For a genuinely new action, terminal cases reject mutation. A stale version returns 409 with `code=STALE_CASE_VERSION`, `current_case_version`, and an instruction to refresh the report; it never automatically retries approval. `CREDIT_INELIGIBLE` includes safe findings and the new diagnostic observation ID. `OUTPUT_ALLOCATION_CONFLICT` reveals no foreign invoice ID, amount, or merchant details.

Absent/revoked/expired credentials return 401; unknown/foreign cases or verification references return 404; malformed fields/keys return 422. Integrity failures and bounded lock conflicts return 409; database failures return a generic 503. Responses use `Cache-Control: no-store`. A failed business commit leaves no decision, evaluation, allocation, event, retry outcome, or case change; its separately committed refresh observation may remain.

## Reports and history

The existing `/report` route now returns `MerchantCaseReportV1`, extending the initial fields with `decisions`, `decision_evaluations`, and `decision_observations`. Initial offline verifier results and evaluation snapshots remain unchanged. The ordinary `/api/cases/{id}` detail route is unchanged.

- No recorded decision: `report_scope=INITIAL_OFFLINE`, possibly with blocked-approval diagnostics.
- Recorded ordinary decisions: `MERCHANT_DECISIONS`.
- Any decision referencing a simulated observation: `SIMULATED_DECISIONS`.

Current report balances still use approved allocation rows and the latest/selected candidate; they are not an offer of automatic approval and their `eligible_for_credit` remains false. Stored decision evaluations explain historical eligibility and policy/source inputs. All report components are read from one repeatable-read snapshot. Legacy resolution rows remain assertion views without invented decision context.

Decision reasons, recovered fields, snapshots, and observation provenance are outside application encryption and disclosed only to the owning merchant. Original receipt/raw-tx strings remain encrypted; reports exclude OCKs, ciphertext, and keys. Audit events contain safe references plus an outcome hash rather than duplicating the reason or recovered fields. Reads/replays validate linked snapshots, invoice/verification/observation context, allocation details, and the event chain. Hashes and immutable triggers are not signatures or protection against a database administrator rewriting records.

Migration `0007` leaves legacy resolution/allocation context null. New records have scoped foreign keys and immutable evaluation/retry records. Downgrade serializes with authorization and workflow writers, then refuses to discard any decision, scoped allocation, or decision-observation diagnostic, including a failed approval. Use forward migrations for accepted history; stop traffic before planned rollback.

## Isolated first-slice demo

Build the verifier, then point the harness at a **disposable PostgreSQL database** using the existing test URL variable:

```sh
ZECSOLVE_TEST_DATABASE_URL='postgresql+psycopg://zecsolve:zecsolve@127.0.0.1:54329/zecsolve' \
  uv run --locked python scripts/demo_resolution.py
```

The script creates a randomly named `zecsolve_demo_*` schema, migrates it, provisions an ephemeral merchant/key, calls the same application services as HTTP, and drops only that schema afterward. It never uses `ZECSOLVE_DATABASE_URL` or persists demo credentials. Supply a role permitted to create/drop schemas, and retain no real data in this demo schema.

Expected output explicitly says `source_kind=SIMULATED` and `live_confirmation=false`. Real recovery returns 100,000 zatoshis; offline approval is blocked. Simulated merchant approval against a 200,000-zatoshi invoice yields 100,000 credited, 100,000 outstanding, and zero remaining candidate for that output. Retry returns the same resolution, a second invoice conflicts, and tampered evidence remains invalid without credit. The JSON trace records safe reference IDs and confirms schema cleanup. This demonstrates workflow accounting, not live chain inclusion or release readiness.

Contracts: [request](../contracts/case-resolve-request.schema.json), [outcome](../contracts/resolution-outcome.schema.json), and [extended report](../contracts/merchant-case-report.schema.json). The trusted observation adapter, grants/sessions, claims/listing and replay exports are implemented. M3.1 live validation merged in PR #27, P4 browser acceptance in PR #26, and deployed browser CI in PR #28; full release operator/team gates remain open; see the [release evidence index](release-evidence.md).
