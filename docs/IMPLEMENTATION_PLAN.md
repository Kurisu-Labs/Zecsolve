# Zecsolve — Remaining P0 Implementation Plan

**Baseline:** October 10, 2026

**Requirements:** [PRD](PRD.md), especially §§6–7 and acceptance scenarios A-01 through A-15

**Status:** Proposed implementation sequence; no application changes or new acceptance results are represented by this document

**First milestone:** Invoice → receipt verification → merchant-approved allocation → report

**Confirmed sequencing:** Start with the public historical fixture and explicitly simulated test confirmations; add trusted live confirmation before release

## 1. First deliverable and boundaries

Build one backend workflow through the real Rust verifier, real PostgreSQL transactions, and a versioned JSON case report before building the full frontend. An integration test and a local demo script must exercise the same application services that the HTTP routes call.

### First-slice acceptance

1. Provision a merchant credential and create an immutable mainnet Orchard invoice for **200,000 zatoshis**, using the receiver and memo from the existing public fixture.
2. Open a case, upload the existing receipt and raw transaction, and persist the real verifier result. Do not synthesize recovered fields.
3. With the offline observer, report `VALID` receipt evidence, `UNAVAILABLE` chain observation, **0 credited**, **200,000 outstanding**, **100,000 candidate**, and **100,000 projected outstanding**. Approval must be blocked.
4. In the isolated test/demo harness only, inject a clearly labeled simulated confirmed observation bound to the verified transaction. The merchant explicitly approves the recovered output through the normal resolution service.
5. Commit exactly one allocation for **100,000 zatoshis**, its merchant resolution, the decision's evaluation snapshot, and its event. The report now shows **100,000 credited**, **100,000 outstanding**, and **0 candidate** for that allocated output. The partially paid case remains open for further evidence.
6. Retry the same approval, then submit the same output against a second invoice. The retry adds nothing; the second invoice receives a conflict without learning the first invoice's private details.
7. Verify the tampered fixture and show invalid evidence with no allocation. Export the initial merchant report containing the inputs, findings, and decision references; the complete replay packet follows in M5.

**Development proof and release proof are separate:** simulated confirmation enables workflow tests, not a claim of observed chain inclusion. M3 replaces the simulated observer with a trusted live source for release validation. No production route or request field can create a trusted confirmation.

### Implementation defaults

- Retain FastAPI, SQLAlchemy/Alembic, PostgreSQL, the existing Rust/Glasspane wrapper, and Vue 3/TypeScript/Tailwind. Keep synchronous bounded verification for P0; do not introduce a queue or microservices.
- Keep receipt-result schema version 1 and the existing POC endpoint compatible. Add separate workflow/report contracts instead of overloading `VerificationReport.chain_state`.
- Provision merchant access through an operator CLI for the hackathon. No signup, email delivery, wallet authentication, or identity-verification product is required.
- Use a same-origin deployment: FastAPI serves the built Vue application and `/api`; Vite proxies `/api` in development. This removes a separate frontend-hosting dependency from P0. Vercel can remain a later hosting choice.
- Use one case per invoice snapshot in P0. Multiple approved outputs can accumulate on that invoice. Do not implement split allocations, allocation reversal, or reassigning an approved output.
- Default invoice policy: ten confirmations for credit, an observation no more than 60 seconds old at commit, exact memo binding, and no overpayment approval. These are explicit engineering defaults, stored with the invoice, not a guarantee against reorganization.
- Leave `unique_receiver_binding=false` in the public P0 workflow. No registry currently proves receiver uniqueness, so callers must not be able to assert it. Missing memo evidence remains reviewable but cannot bypass binding requirements.
- Operate the hackathon demo with public fixtures. Real customer onboarding remains gated on documented retention/deletion terms and deployment controls from the PRD; do not describe the demo as a production pilot.

## 2. Repository gaps that affect the design

| Existing foundation | Remaining integration work |
|---|---|
| Pure `evaluate()` function sums approved allocations | Load authoritative allocations from PostgreSQL, preserve evaluation inputs, and apply versioned confirmation/freshness policy |
| Output identity is the allocation primary key | Catch conflicts in the service and serialize approvals on an invoice so different outputs cannot both pass a stale balance check |
| Immutable invoice, verification, resolution, allocation, and event records | Add transactional writers and retain event payloads; hashes alone are insufficient to reconstruct event history |
| `Verification` points to one non-null `Evidence` record | Treat a submission as an evidence bundle containing receipt/raw-tx components, including missing components, without fake receipt data |
| `ChainObservation` has a table | Add an observation adapter, transaction binding/provenance, append-only observation history, and release validation |
| A single POC token protects stateless verification | Add merchant-bound principals, revocable credentials/sessions, and case-scoped customer/reviewer grants |
| `Case.version` exists | Check it on new decisions, increment it on workflow mutations, and return it in reports |
| `policy_version` and `rules_version` fields exist | Persist the policy configuration and exact historical evaluation used for every decision |
| Readiness and a migration test expect revision `0001` | Compare the database revision with the packaged Alembic head after adding migrations |
| Database tests insert independent synthetic records | Add API/service tests proving relationship authorization, atomicity, idempotency, and rollback together |

Primary implementation references: [models](../apps/api/src/zecsolve/db/models.py), [rules](../apps/api/src/zecsolve/domain/rules.py), [API assembly](../apps/api/src/zecsolve/main.py), [verifier adapter](../apps/api/src/zecsolve/adapters/verifier.py), and [initial migration](../apps/api/migrations/versions/0001_initial_schema.py).

## 3. Build sequence

Each milestone should be reviewable and runnable before the next is considered complete. The dates in PRD §9 remain the delivery target; gates below establish completion, not an assumed number of engineering hours. Owners are unassigned.

| Milestone | Deliverable | Depends on | PRD coverage |
|---|---|---|---|
| M1 | Authenticated invoice, case, private evidence, and persisted real verification | Existing foundation | P0-01, P0-02, P0-05, merchant portion of P0-06 |
| M2 | Atomic merchant allocation and initial report; first vertical slice complete | M1 | P0-03, P0-04, core P0-07 |
| M3 | Trusted live confirmation and failure-path hardening | M2 | P0-02, P0-04, P0-05 |
| M4 | Customer/reviewer grants, disclosure consent, and scoped views | M2 | Remaining P0-01 and P0-06 |
| M5 | Authorized replayable packet and replay command | M3, M4 | P0-08 |
| M6 | Merchant/customer/reviewer Vue flows | M2 contracts; M4/M5 for completion | P0-07 |
| M7 | Release rehearsal, deployment controls, and evidence collection | M1–M6 | P0-09 and all acceptance gates |

### M1 — authenticated invoice to persisted verification

**Application structure:** keep route handlers thin. Add `api/` routers, `services/` workflow/report functions, `auth/` dependencies, and workflow schemas under the existing Python package. Reuse `domain/` for pure rules and `adapters/` for bounded external work. A SQLAlchemy session belongs to one request/service unit of work; never share sessions across threads.

**Identity:** introduce principals tied to a merchant, hashed high-entropy credentials with expiry/revocation, and an operator provisioning command. Use opaque random credentials, not the shared POC token, for workflow access. Return the bootstrap credential once; store only its digest. Derive merchant/actor identity server-side on every request. An authenticated request for an inaccessible case or invoice returns 404 without revealing its existence.

**Invoice:** accept integer `expected_zat`, mainnet network, supported shielded pool, receiver address, optional memo text, and expiry. Normalize the receiver in Rust using the already-pinned `zcash_address` dependency via a separate bounded `normalize-address` mode; preserve the current verification CLI invocation. Reject mismatched network, invalid addresses, or an address lacking the requested receiver. Never accept client-supplied normalized bytes as authoritative. Encode memo text as UTF-8, reject values over 512 bytes, and right-pad to 512 bytes; preserve the original text and exact comparison bytes. Null means no expected memo.

Create invoice and immutable policy snapshot together. Hash a deterministic representation of the exact invoice terms and policy reference. A new invoice's policy is fixed at creation. Retain unsupported historical rows for inspection; do not invent missing policies for them or allow them to receive credit until explicitly reviewed.

**Case:** create a merchant-owned case against that invoice; enforce uniqueness of `invoice_id` for this P0 workflow. Record a `CASE_OPENED` event. Claims are optional assertions with a server-derived claimant role and principal/grant reference.

**Evidence:** save one bundle per submission, with an optional receipt and optional raw transaction. A bundle is still a real submitted record when a component is absent; it does not fabricate evidence. Preserve original UTF-8 strings/bytes and their hashes separately from the decoded raw-transaction hash. Reuse the current request/body and per-component size limits.

Store encrypted bundle content in PostgreSQL `BYTEA`, with metadata and an opaque storage reference. This lets metadata and content commit together without an object-store cleanup workflow. Use the `cryptography` library's AES-GCM, a fresh 96-bit nonce per encryption, a configured 256-bit secret key, and associated data binding merchant, case, evidence ID, and payload version. Persist key ID, nonce, and ciphertext; keep key material outside the database and out of logs. Enforce nonce uniqueness per key ID. Follow the [library's authenticated-encryption API](https://cryptography.io/en/stable/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM).

This protects original evidence blobs; existing invoice fields and recovered result records still require encrypted database volumes/backups and restricted database access. Do not claim application-level encryption covers every field.

**Verification:** authorize before loading/decrypting a bundle. Run `VerifierAdapter` outside any row-locking transaction, sharing the existing concurrency limiter across POC and workflow verification. Reauthorize when persisting, and reject attaching evidence from another case. Persist the complete immutable verifier result, an initial chain observation, an evaluation, and a case event. A `NONE`, `UNSUPPORTED`, `UNAVAILABLE`, or `ERROR` result is still a recorded attempt with its own reason; it is not an allocation.

For expensive verification retries, check for a completed idempotency result before running Rust and claim the key again in the short persistence transaction. Concurrent executions may perform the bounded read-only verification twice, but only one attempt/event is persisted for that key; the loser returns the recorded result. Do not hold database locks while waiting for the subprocess. A new key permits a deliberate new attempt after a technical failure.

**Gate:** an authenticated integration test creates invoice/case/evidence, calls the real Rust verifier, and reads the expected unapproved balances from the report. Another merchant cannot obtain those records. The offline observer produces unavailable status and blocks approval.

### M2 — merchant-approved allocation and reasoned report

Implement the resolution protocol in §5 before adding UI approval controls. Introduce typed resolution actions: `APPROVE_OUTPUT`, `REQUEST_EVIDENCE`, `REJECT_EVIDENCE`, and `CLOSE_UNRESOLVED`. Every action requires a reason; approval/rejection references a verification from the same case.

Extend the pure evaluation boundary with typed policy and chain-observation inputs, an injected evaluation time, and explicit freshness/confirmation findings. Increment `RULES_VERSION` for this behavior change and preserve the previous implementation for replay. Keep the returned balance fields and multi-finding behavior. A chain observation may be `CONFIRMED` but still below the invoice's required confirmation count; report that distinction instead of rewriting it as unconfirmed.

Add one report assembler used by `GET /api/cases/{id}`, the future UI, and the export service. It must show invoice terms, case version/state, claims as assertions, per-attempt verification/observation results, current approved balance, the selected candidate projection, decision history, and evidence provenance. Historical decision snapshots and current balances must be labeled separately.

The local demo harness must call the same routes/services as normal operation, use a disposable database/schema, run the real fixture verifier, and label injected observations `source_kind=SIMULATED`. Simulated observers and the policy permitting them exist only in test/demo composition, not in the deployed ASGI app or a public configuration toggle. The deployed app rejects simulated observations for credit even if such rows are present.

**Gate:** all seven first-slice steps in §1 pass, plus same-invoice concurrent retries, different-output concurrent approvals, and rollback after an injected event-write failure. No orphan resolution or allocation may survive a failed transaction.

### M3 — trusted live confirmation and negative paths

Implement a `ChainObserver.observe(network, txid, expected_raw_tx_sha256)` port. Keep an offline implementation and add a read-only Zebra-compatible JSON-RPC implementation using a server-configured endpoint. Promote the existing HTTP client dependency to runtime and use bounded timeouts/response sizes. Do not accept URLs, credentials, or confirmation assertions from customer input.

Use `getrawtransaction` with verbose output for the verified transaction ID; compare the returned decoded transaction hash with the verified raw bytes. Require correct network from `getblockchaininfo`, a current/synced source, and best-chain inclusion before returning a confirmed observation. Use the containing block's `getblockheader` result to verify its height/hash and current best-chain confirmations. Preserve source ID, observed time, transaction binding, block data, and the sanitized relevant response fields. Zebra documents these fields and their mempool/side-chain distinctions in its [transaction response](https://zebra.zfnd.org/internal/zebra_rpc/client/struct.TransactionObject.html), [block-header response](https://zebra.zfnd.org/internal/zebra_rpc/methods/struct.BlockHeaderObject.html), and [chain-info response](https://zebra.zfnd.org/internal/zebra_rpc/methods/struct.GetBlockchainInfoResponse.html).

The adapter must verify the selected node's actual response format during integration rather than treating Rust documentation field names as JSON field names. Record the tested node version and endpoint capabilities. Configuration is a deployment dependency; no endpoint is assumed to exist today.

- No RPC configuration, timeouts, authentication failures, malformed/missing fields, unsynced source, or ambiguous lookup failure → `UNAVAILABLE`, with a diagnostic reason.
- A supported response showing mempool or side-chain placement → `UNCONFIRMED`; a “not found” response alone is not a receipt-invalid result.
- Best-chain inclusion → `CONFIRMED` with observed count; credit additionally requires the stored policy threshold and freshness.
- Raw-byte or network mismatch → untrusted/unavailable observation with a binding failure reason; preserve the independent receipt result.

Refresh the observation before every new credit decision, outside the database lock transaction; recheck its age after locks are acquired. Do not keep using an older successful observation when the refresh fails. If a reorganization is observed later, retain the original approval record, flag the case for review, and block additional credit based on the invalidated observation. Automatic reversal is outside P0.

Use HTTPS for remote RPC, allow plain HTTP only for explicitly configured local/private infrastructure, disable redirects, and store credentials as secrets. A chain lookup discloses a transaction ID to that provider, never the receipt OCK or memo; disclose this in the case consent/help text.

**Gate:** run the historical fixture through the workflow with a real configured node and record the returned chain evidence, then approve using a merchant credential. Run adapter tests for insufficient confirmations, stale observations, missing transaction, wrong network/raw bytes, side chain, timeout, and request-supplied confirmation spoofing. Live access is required before marking the release credit path complete.

### M4 — customer/reviewer access and consent

Add merchant-created, expiring, revocable case grants. Customer grants permit claim/evidence submission and a minimal acknowledgement; they do not expose all case evidence or permit verification/approval. Reviewer grants permit the selected report fields and an explicit allowlist of evidence bundle IDs, with export enabled only when separately granted.

For browser access, exchange the initial access code for a server-side session in an HttpOnly, Secure, SameSite cookie; enforce trusted Origin plus CSRF protection for state-changing cookie-authenticated requests. Use an eight-hour session maximum and cap it at credential/grant expiry. Recheck the underlying credential/grant on every request so revocation also invalidates active sessions. Use a fragment or manual entry for the initial grant code; strip it after exchange and never store it in localStorage or query-string logs.

Consent version 1 records the submitting principal/grant, case/evidence, disclosure text version, time, permission for the merchant to process the bundle, and whether the bundle may be shared with reviewers. Default reviewer sharing to false. A merchant cannot grant a reviewer evidence lacking the required sharing authorization. Already-public fixtures are labeled as public source material, not customer consent.

Build explicit response projections by role; do not serialize the ORM case object and remove a few fields afterward. Recipient/memo fields, claims, other reviewers, decision reasons, and other submitted evidence can all reveal information. Default reviewer views to selected information only. Redact cross-merchant allocation conflicts to an opaque conflict indicator.

**Gate:** test two merchants, a customer grant, a report-only reviewer, and an evidence/export reviewer against every route. Include expired/revoked grants and sessions, unconsented evidence, guessed IDs, overbroad evidence IDs, direct download/export attempts, and memo markup injection. Explain that revocation cannot retract downloaded receipt copies.

### M5 — replayable export

Implement `CasePacketV1` and a local `replay-case` command. Build the packet from a consistent database snapshot, not separately timed queries that mix balances and decisions. Reuse the role projections from M4.

The packet contains the PRD §6.5 materials: invoice/policy, claims, exact receipt/raw transaction bytes with encodings/hashes, provenance and historical observations, verifier result and dependency revision, evaluation/rules version and owned allocation inputs, resolutions, and replayable event payloads. Embed binary content as base64; distinguish original-file hashes from decoded raw-transaction hashes. Include an integrity manifest and the report's data/disclosure mode.

Replay uses only bundled bytes and recognized verifier/rules versions. It does not fetch arbitrary URLs, execute code from a packet, or promote historical observations into fresh confirmation. Report separate outcomes for cryptographic recovery, arithmetic/rules reproduction, integrity, and assertions that cannot be independently established. Preserve access to the old rules version when the current one changes.

Use a deterministic JSON serialization profile for project-produced hashes: sorted object keys, compact separators, UTF-8, no floats/NaN, normalized UTC timestamps, and byte strings encoded explicitly. Document the profile version; do not claim general cross-language canonical JSON support without proving it.

For a cross-merchant conflict, include only a scoped assertion that the output was allocated elsewhere, never the foreign invoice/merchant record. Mark conflict truth as an external assertion and the packet `replay_scope=SCOPED`. Evidence omission/redaction must produce a limited report with explicit missing inputs, not a false full-replay success.

**Gate:** export/replay a valid approved case and the tampered case, modify one byte and observe integrity failure, and test missing/unsupported replay versions. Verify snapshot consistency during a concurrent approval and ensure all role/consent restrictions also apply to exports.

### M6 — Vue user flows

Create the frontend in `apps/web` using the established Vue/TypeScript/Tailwind choice. Generate TypeScript API types from OpenAPI after M2 freezes the first workflow contract. Start with a merchant case page; add the customer/reviewer views after their projections exist.

- **Merchant:** enter invoice terms, open/view a case, upload/select evidence, run verification, inspect independent statuses/balances, approve with a reason, request more evidence, reject evidence, close unresolved, manage grants, and download an authorized report/packet.
- **Customer:** review disclosure text, consent, submit a claim and optional receipt/raw transaction, and receive an acknowledgement without exposure to other evidence.
- **Reviewer:** inspect explicitly shared report sections/evidence, understand proof limits, and export only when granted. No merchant write actions are shown.
- Render ZEC from integer zatoshis using exact string conversion. Keep raw integer values in API calls and distinguish credited, outstanding, candidate, and projected balances.
- Approval controls reflect server eligibility but never replace server checks. Use one persistent idempotency key for a pending action, disable duplicate clicks, and recover the same outcome after a lost response. Refresh on a stale case version.
- Display receipt, chain, case, and business status independently, including simulated-source labels. Render memo/notes as text, with keyboard-accessible forms, labeled errors, loading states, and visible unavailable/unsupported states.

**Gate:** browser tests exercise the first slice, same-invoice retry, cross-invoice conflict, tamper rejection, missing receipt, below-threshold confirmation, and customer/reviewer restrictions against the actual backend. Isolated test observations must be visibly labeled.

### M7 — release, controls, and evidence

Bundle the Vue build with the existing unprivileged backend image, preserve migration-before-start behavior, and provide a same-origin TLS ingress. Keep the public POC verifier disabled in the release environment; grant access only to the workflow routes. Add ingress request/rate limits and container CPU/memory limits while retaining the bounded verifier adapter.

Readiness must check the actual packaged migration head, executable availability, and evidence-encryption configuration. Expose chain-observer availability as a separate capability so an RPC outage does not falsely claim verification failure or erase usable reports. Log correlation IDs, durations, sanitized reason codes, and allocation-conflict counts; exclude tokens, receipt content, RPC credentials, and recovered memo/receiver data.

Rehearse migrations on a disposable copy, verify database encryption/backups and restore of encrypted evidence with the correct external key, and test recovery after a lost response and application restart. Roll back application images only when schema-compatible; do not downgrade away accepted allocations. Disable new approvals if rollback cannot preserve invariants.

Capture commands/results with revision, environment, and time. Record the three demo scenarios, export replay, known limitations, and live chain validation. Conduct the PRD's two discovery conversations and record actual results, including negative feedback; this plan does not authorize contacting anyone automatically.

**Gate:** all P0 acceptance rows have evidence or an explicit incomplete status. Keep the October 12 submission target and October 13 contingency window from the PRD; lack of live confirmation means the full credit path is not release-complete, even if the fixture demonstration works.

## 4. Data, interface, and migration changes

### Persisted additions

Use forward Alembic revisions after `0001`; do not rewrite the existing migration. Split additions into a core workflow revision for M1/M2 and an access/export revision for M4/M5.

| Addition | Required purpose and invariants |
|---|---|
| Principals, credential digests, and sessions | Bind actors to merchants; support expiry/revocation; never persist raw access secrets |
| Immutable policy snapshots | Store the confirmation threshold, freshness window, memo-binding policy, and rules version selected for each new invoice |
| Evidence bundle metadata and encrypted payload | Bind receipt/raw-tx components, original hashes, source, submitter, and ciphertext to a single case |
| Append-only evaluation records | Preserve invoice/policy reference, verification/observation reference, evaluation time, owned allocation inputs, findings, balances, and final credit eligibility |
| Resolution evaluation reference | Tie each new decision to the exact evaluated state and source evidence, without rewriting the receipt result |
| Idempotency records | Unique principal/merchant + method + route/resource + key; store normalized request digest and resulting resource/outcome |
| Chain observation provenance | Bind an observation to network, txid, decoded raw-tx hash, source kind/ID, observation time, and relevant response data; retain all attempts |
| Event payloads | Store safe structured event content alongside the existing hashes and sequence; no secret evidence bytes in event payloads |
| Grants and consent records | Bind access/disclosure to the case and explicit evidence selections, with expiry/revocation and immutable consent history |

Preserve current rows. New references can initially be nullable for legacy records, but new service writes must provide them and legacy rows cannot become credit-eligible through guessed context. If adding uniqueness discovers duplicate invoice cases, fail the migration with a remediation report instead of deleting or merging records. Extend immutability protections to policies, evaluations, observations, and evidence metadata; credential/grant revocation and encrypted-content deletion are separate lifecycle operations.

Do not add invoice editing to P0. A merchant can close an uncredited case and create a new snapshot for corrected terms. A credited invoice cannot be replaced in a way that silently moves its allocations; that requires a later explicit correction/reversal design.

### Minimum workflow API

All successful workflow responses carry stable IDs and a report/schema version. Mutating workflow POSTs accept an `Idempotency-Key`; authorize first, then validate/replay it. Unknown request fields are rejected. Money is integer zatoshis; times are timezone-aware UTC; actor/merchant identity and chain trust are never client-controlled.

| Route | Minimum input | Result / authority |
|---|---|---|
| `POST /api/invoices` | Expected integer amount, network/pool, receiver address, memo text or null, expiry or null | Immutable snapshot plus server-selected policy; merchant only |
| `POST /api/cases` | Invoice ID | Case ID/state/version; merchant only |
| `GET /api/cases` | Cursor and optional state filter | Merchant-owned case summaries; add this read route for the dashboard |
| `GET /api/cases/{id}` | Case ID | `CaseReportV1`, projected for the caller |
| `POST /api/cases/{id}/claims` | Optional reported txid and note | Assertion record; merchant or scoped customer |
| `POST /api/cases/{id}/evidence` | Optional receipt/raw-tx strings, optional claim ID, source label, consent acknowledgement | Evidence bundle ID; merchant or scoped customer; source label is not a trust grant |
| `POST /api/cases/{id}/verify` | Evidence bundle ID | Persisted result, observation, evaluation, and updated case version; merchant only in P0 |
| `POST /api/cases/{id}/resolve` | Action, verification ID where required, expected case version, reason | Resolution/allocated output reference and post-decision balances; merchant only |
| `POST /api/cases/{id}/grants` | Customer/reviewer role, expiry, allowed report/evidence selections, export permission | One-time access code plus grant metadata; merchant only |
| `DELETE /api/cases/{id}/grants/{grant_id}` | Grant ID | Revocation; merchant only; already-revoked is harmless |
| `GET /api/cases/{id}/export` | Case ID | Complete or explicitly scoped/limited `CasePacketV1`; authorization rechecked |
| `POST /api/session`, `DELETE /api/session`, `GET /api/session` | Initial access code for creation | Browser session creation, logout, and current access scope |

Creation normally returns 201; reads and recorded-action replay return 200. Use 401 for missing/invalid credentials, 403 for a forbidden action on an otherwise accessible case, 404 for inaccessible objects, 409 for stale versions/idempotency mismatch/allocation conflict or ineligible business actions, 413 for limits, 422 for input validation, and 429 for verifier capacity. A completed verification attempt with an unsuccessful receipt state returns its domain result, not a misleading server failure.

Keep `CaseReportV1` separate from the existing receipt result. Include `case`, `invoice`, `policy`, `claims`, `evidence`, `verifications`, `chain_observations`, `evaluations`, `balances`, `resolutions`, `events`, and `disclosure_scope`, projected for the role. Approval input does not contain amount, receiver, output identity, approved-by identity, or trusted chain state; the service derives them from authorized stored records.

## 5. Approval transaction and state behavior

### Credit protocol

1. Authenticate/authorize the merchant and load the requested case/verification relationship. Check for an already completed idempotency result or same-invoice output allocation before external work; reauthorization always precedes replay.
2. For a genuinely new approval, refresh chain evidence outside the database transaction. Persist the immutable observation attempt. Failure leaves a useful diagnostic but cannot create a resolution or credit.
3. Begin a short transaction and claim the idempotency record. Use a unique insert/row lock so concurrent requests with the same key serialize. A different normalized body for that key returns 409. Exclude the idempotency header itself from the body digest.
4. Lock the immutable invoice row for allocation coordination, then the case row, always in that order. `SELECT FOR UPDATE` locks a row without modifying the invoice snapshot. All invoice-affecting writers follow this order. PostgreSQL documents the relevant [row-lock behavior](https://www.postgresql.org/docs/17/explicit-locking.html).
5. Recheck relationships and current authorization, then the semantic output allocation. If already allocated to this invoice, return the original allocation/resolution outcome without another decision event; this check precedes stale-version rejection for a completed retry. An allocation to another invoice produces an opaque conflict.
6. For a new allocation, compare the expected case version, require a nonterminal case, and check that the fresh observation still meets its age bound. Load all approved allocations for this invoice and the candidate output's global allocation status. The global lookup is internal and must not reveal foreign case details.
7. Re-evaluate the immutable invoice/policy, verification, observation, and current approved allocations. Block invalid/unsupported/unavailable evidence, missing reference binding, recipient mismatch, insufficient/stale confirmation, conflict, or projected overpayment. Derive the allocation amount from the recovered output only.
8. Write the decision evaluation, merchant resolution, full-output allocation, case state/version update, event with chained hash, and successful idempotency result in the same transaction.
9. Commit once. On allocation uniqueness failure, roll back the entire decision transaction, reread the winning allocation in a fresh transaction, and return same-invoice replay or cross-invoice conflict. Do not leave a resolution behind from the losing attempt.

Different outputs on one invoice serialize through the invoice lock, so each decision sees the latest approved balance. Competing invoices for one output are protected by the allocation primary key. A crash before commit leaves no business side effects; a lost response after commit is recovered by the same key or semantic output lookup.

Limit database lock waits to five seconds and return a retryable conflict without partial writes when exceeded. Idempotency records contain safe resource/outcome references, not raw evidence or credentials, and are retained for the life of the case. Replay reconstructs the original safe outcome after current authorization checks. Non-credit decisions also require idempotency but never create allocations.

### States and audit events

- New case → `OPEN`; missing required evidence or a merchant request → `AWAITING_EVIDENCE`; a persisted usable attempt or evidence rejection awaiting another attempt → `UNDER_REVIEW`.
- An approved partial payment leaves `UNDER_REVIEW`. A fully covered invoice after explicit approval can close that case as `RESOLVED`. `CLOSE_UNRESOLVED` writes `CLOSED_UNRESOLVED` without credit.
- Terminal cases reject new mutations except semantic/idempotent retries of completed actions. Invoice balance remains separately visible; terminal status does not override arithmetic.
- Increment `Case.version` for accepted workflow mutations and append a monotonically sequenced case event under the case lock. Store action, actor, UTC time, safe payload, its hash, previous event hash, and the event hash. Hash the serialized payload separately; hash the event's case ID, sequence, actor, action, time, payload hash, and previous hash using the same versioned serialization profile. The first previous hash is null; never include an event's own hash in its hash input.
- A stale decision returns the latest version and a safe refresh instruction, not an automatic retried approval. The merchant must review changed balances/evidence.
- Reports never overwrite historical approval context with newer observation results. Current warnings and historical decisions can coexist.

## 6. Test plan and traceability

Use real PostgreSQL for transactions/locks and the real Rust binary for cryptographic cases. Mock only the external chain observer when a scenario requires deterministic confirmation; identify those tests as simulated-source tests. SQLite and mocked database inserts cannot demonstrate the allocation guarantees.

| Test group | Required assertions | PRD scenarios |
|---|---|---|
| First vertical slice | Offline blocks approval; simulated-source harness approves only on merchant action; balances and report are correct | A-01, A-03, A-10 |
| Aggregate payments | Two approved synthetic outputs of 600,000 and 400,000 cover 1,000,000; label these rule/service inputs synthetic, not additional historical crypto fixtures | A-04 |
| Retry after response loss | Same key/body replays; changed body conflicts; different key/same allocated output adds no resolution, event, or credit | A-05 |
| Concurrent approval | Same output/same invoice commits once; same output/two invoices has one winner; different outputs/one invoice recheck the total and cannot bypass overpayment review | A-06 |
| Output identity | Distinct outputs in one tx are independent; changing pool/network/index cannot bypass binding or allocation identity | A-02, A-07 |
| Failure/rollback | Tamper, wrong txid, bad index, missing input, unsupported format, timeout, malformed raw tx, and injected write failures produce no partial credit | A-02, A-08, A-14 |
| Binding and policy | Normalize equivalent receiver encodings; reject mismatched pool/network, missing reference binding, unsafe candidate amount, insufficient confirmations, and stale observation | A-09, A-10 |
| Chain trust | Ignore forged request fields; verify raw bytes/network; preserve unavailable/not-found/side-chain distinctions; refresh failure cannot reuse stale success | A-08, A-10 |
| Access and consent | Two merchants plus all grant scopes; revoked/expired sessions, unconsented evidence, arbitrary IDs, export/download restrictions | A-11, A-12 |
| Export/replay | Original bytes and policy/rules context survive; tampering fails integrity; historical math reproduces; foreign conflicts remain scoped; concurrent export is internally consistent | A-13 |
| History and migration | No invoice edits or partial decision rows; event chain is reproducible; migrate existing records without inventing policy; readiness tracks head | A-14 |
| Operational/browser | Request/process limits, secret redaction, safe memo rendering, complete user flows, restart/retry, encrypted restore, and clean deployment | A-15 and P0-07 |

Run the existing verifier/rules/API suites after integration changes and `make test-db` for every schema/allocation change. Add targeted service/API tests under the existing test tree and browser tests in the frontend package. Generate OpenAPI types and check them for drift; regenerate the existing verifier schema only if its actual model changes.

The previous documentation session could not start `make test` because Cargo was unavailable; Cargo, uv, and a disposable PostgreSQL database must be available before recording implementation results. Do not count source inspection, test presence, or a skipped database suite as a passed acceptance gate.

## 7. Release evidence, dependencies, and immediate next task

### Evidence to retain

- An acceptance checklist with each A-ID, command/scenario, actual outcome, commit/revision, environment, and timestamp.
- A first-slice trace identifying invoice, case, evidence, verification, observation, evaluation, resolution, and allocation IDs; simulated and live traces remain distinct.
- Concurrency/rollback results, scoped-access results, and a sample authorized packet plus replay output.
- Tested RPC node/version and sanitized live chain observation for the historical output; no credentials in the evidence bundle.
- Deployment/restart/restore rehearsal, screenshots, known limitations, the PRD's video artifacts, and actual discovery notes.

### External dependencies and boundaries

- **Live RPC:** the operator must supply a trusted compatible endpoint before M3's release gate. Until then, complete the fixture slice and deterministic tests; keep real credit blocked rather than treating availability as confirmation.
- **Credentials and encryption:** provision access credentials and the evidence key through local operator tooling and deployment secrets. Never place them in the repository or shared reports.
- **Private-data retention:** before a real customer pilot, specify retention/deletion for original bundles, derived verification fields, invoice/claim/decision data, and backups together. Implement an authorized purge process consistent with the append-only application's limits. Expiring only the original blob while retaining all recovered personal fields is insufficient. This gate does not prevent a public-fixture hackathon demo.
- **P1 exclusions:** no CipherPay adapter, notifications, refund execution, signed report, browser WASM, CSV, or new-chain/transaction-format work on this path.

**Immediate implementation task:** M1's core workflow migration, merchant provisioning/auth dependency, receiver normalization, invoice/case creation, encrypted evidence bundle, persisted verifier call, and an initial `CaseReportV1`. Its first test must demonstrate the real historical output with zero credited balance and blocked offline approval. Then implement M2's transaction protocol without introducing a demo-only allocation shortcut.

### Sources checked for the proposed approach

- [PRD](PRD.md), [Preflight](../instructions/Preflight.md), [teammate guide](../TEAM_GUIDE.md), and [security boundaries](security.md).
- [Existing database tests](../apps/api/tests/test_postgres.py), [rules tests](../apps/api/tests/test_rules.py), [verifier tests](../apps/api/tests/test_verifier.py), and [API tests](../apps/api/tests/test_api.py).
- [PostgreSQL 17 explicit locking](https://www.postgresql.org/docs/17/explicit-locking.html).
- [Cryptography AES-GCM API](https://cryptography.io/en/stable/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM).
- Zebra's [RPC methods](https://zebra.zfnd.org/internal/zebra_rpc/methods/index.html), [transaction object](https://zebra.zfnd.org/internal/zebra_rpc/client/struct.TransactionObject.html), [block header](https://zebra.zfnd.org/internal/zebra_rpc/methods/struct.BlockHeaderObject.html), and [chain info](https://zebra.zfnd.org/internal/zebra_rpc/methods/struct.GetBlockchainInfoResponse.html). Their pages may show different generated crate versions; the configured node's actual API must pass M3's compatibility test.
