# Incremental development

## Item 01 — merchant identity and credentials

Completed locally on October 10, 2026, over baseline commit `951fb34c852ae91c161740cb974090232c2b4523`.
This is the identity portion of M1; the complete invoice/case workflow remains unfinished.

- Migration `0002` adds merchant-bound credentials, unique SHA-256 token digests, expiry, and revocation.
- The operator CLI creates a merchant, issues an additional credential, and revokes an individual credential. Tokens have 256 random bits and are disclosed only after a successful commit. Credentials expire after 30 days by default; supported lifetimes are 1–365 days.
- `require_merchant` derives identity from an active database credential. `GET /api/auth/me` returns merchant/credential IDs without secrets. Invalid credentials return 401; an unavailable database returns a generic 503.
- Readiness compares the database revision with the head of the configured migration directory, rather than a hardcoded initial revision.
- Setup, security, and code-tour documentation describe this increment and its remaining boundaries.

### Recorded validation

Environment: Windows, Python 3.12.14, PostgreSQL 17.11. The database was a disposable loopback-only instance on port 55439, with a separate generated schema for each test.

```text
python -m pytest apps/api/tests/test_auth.py apps/api/tests/test_auth_postgres.py apps/api/tests/test_postgres.py -q
29 passed

python -m pytest apps/api/tests/test_api.py -k 'not honest and not real_recovery' -q
4 passed, 2 deselected

python -m ruff check .
All checks passed

python -m ruff format --check .
38 files already formatted

git diff --check
Passed
```

Database tests cover two merchant identities, spoofed query identity, hashing, expiry, immediate/idempotent revocation, credential rotation, provisioning rollback, CLI disclosure after commit, a deferred failure at COMMIT, preservation of preexisting merchants during migration, and readiness on an older schema. Existing PostgreSQL allocation/immutability tests also passed.

The verifier integration and rule suites were not run in this session because Cargo/the Rust binary were unavailable. No cryptographic recovery or live chain-confirmation result is claimed for this increment. The existing API validation/POC-disabled tests passed. A Starlette warning about its existing httpx TestClient integration remains; no dependency versions were changed.

## Item 02 — mainnet recipient normalization

Implemented on October 10, 2026, over baseline `a5a5955`, in separately committed contract, decoder, CLI, process-runner, adapter, test, and documentation increments.

- Decode mainnet Unified Addresses with the pinned `zcash_address` dependency and select the requested Orchard or Sapling receiver. Standalone Sapling and a Unified Address carrying the same Sapling receiver normalize to identical bytes.
- Validate the selected inner receiver using Orchard/Sapling libraries; valid outer encoding alone is insufficient. Orchard `0.15.0` was already locked transitively and is now a direct dependency; no dependency versions changed.
- Add `normalize-address --input REQUEST_JSON_FILE` alongside the existing receipt verification CLI. Bound request reads, reject unknown fields, and emit an independent version-1 result with an exact-input hash. Normalization remains mainnet-only.
- Add `NormalizeAddressRequest`, `AddressNormalizationReport`, generated JSON schemas, and `AddressNormalizer`. The Python adapter checks the schema, hash, result consistency, and selected network/pool. It distinguishes invalid input from unavailable binaries and execution/protocol errors.
- Share the existing bounded subprocess runner with receipt verification. Tests cover isolated environment/stdin, explicit arguments, private temporary files and cleanup, timeout, closed stdout before exit, output overflow, and unsuccessful exit.
- Preserve the existing receipt CLI, receipt-result schema, historical fixture, and offline chain status. No invoice route, authorization flow, allocation, or live chain integration is introduced.

### Recorded validation

Local environment: Linux, Python 3.14.7, Rust 1.99.0. The installed stable alias was older than the repository's minimum, so validation explicitly selected the CI toolchain; the repository's toolchain policy was not changed.

```text
RUSTUP_TOOLCHAIN=1.99.0 CARGO_PROFILE_DEV_DEBUG=0 CARGO_INCREMENTAL=0 UV_CACHE_DIR=.cache/uv make test lint poc
Rust: 12 passed (2 existing receipt tests, 6 receiver tests, 4 CLI tests)
Python: 76 passed, 17 PostgreSQL tests deselected
Rust formatting and Clippy: passed
Python lint and formatting: passed
POC: unchanged valid/tampered behavior; 0 credited, 100,000 candidate, chain UNAVAILABLE

git diff --check
Passed
```

The existing Starlette/httpx deprecation warning remains. FastAPI TestClient execution stalled inside the local sandbox; the full suite passed when run outside that sandbox. No database schema changes were made, and local PostgreSQL tests were not run; the branch/PR CI runs the database suite separately. A read-only independent review found no actionable issues in the implementation. Synthetic address tests demonstrate decoding, not additional historical Sapling payment recovery or live confirmation.

## Item 03 — immutable merchant invoice and policy snapshots

Implemented on October 11, 2026, over baseline `3c7517f`, with separate commits for contracts, hashing, migration, service, HTTP routes, input/auth corrections, regression tests, schema exports, and documentation.

- `POST /api/invoices` derives merchant identity from an active credential, normalizes the supplied receiver through Rust, and atomically commits invoice terms, server policy, and a scoped creation-retry record. `GET /api/invoices/{id}` returns only owned snapshots.
- New invoice terms contain strictly positive integer zatoshis, mainnet/pool, original receiver address, normalized receiver bytes, optional original memo plus its 512-byte padded representation, and optional UTC expiry. Reject unsupported text, numeric timestamps, already-expired new invoices, and client-supplied identity/policy/normalized fields.
- Preserve a versioned policy with ten confirmations, 60-second observation freshness, exact memo binding, no overpayment approval, and no unique-receiver shortcut. Hash the terms, policy configuration, and owner/invoice/policy IDs with the documented version-1 serialization profile.
- Migration `0003` preserves historical invoices without fabricating policy. Add same-merchant foreign keys and immutable invoice/policy/retry records. Downgrade refuses to discard policy evidence on populated new invoices.
- Same credential/key/body replays with 200; new creation returns 201; changed bodies conflict. Concurrent equal requests produce one persisted result, and conflicting requests have one winner. Failed commits leave no partial policy, invoice, or retry record.
- Recheck authorization around normalization and inside database transactions. Acquire the credential lock before comparing a fresh database clock, including GET/replay, so expiry during lock waits cannot grant access. Share the existing subprocess capacity and hold no database locks while Rust runs.

### Recorded validation

Local Linux, Python 3.14.7, Rust 1.99.0, and a disposable loopback-only PostgreSQL 17 container with a unique schema per test:

```text
make test: 12 Rust tests passed; 92 Python tests passed, 45 PostgreSQL tests deselected
make test-db: 45 passed, 92 deselected
make lint: Rust formatting/Clippy and Python lint/formatting passed
make poc: original valid/tampered recovery and offline balances preserved
Schema regeneration, local documentation links, and git diff --check: passed
```

Commands explicitly selected `RUSTUP_TOOLCHAIN=1.99.0`, disabled local debug info/incremental builds, and configured the disposable test database. The existing Starlette/httpx deprecation warning remains. Independent review identified input and credential-expiry edge cases; regression tests reproduced them, fixes passed, and follow-up review found no remaining blockers in this increment.

This is still part of M1. Invoice creation does not create a case, allocate payment, or perform chain confirmation. See [the invoice API guide](invoices.md) for request/replay behavior, hashing, and migration limitations.

## Item 04 — merchant case opening and initial audit event

Implemented on October 11, 2026, over baseline `9c6087a`, with separate commits for contracts, shared workflow safeguards, migration, service, HTTP routes, review fixes, schema exports, regressions, and documentation.

- `POST /api/cases` accepts only an owned, supported invoice ID. Create an `OPEN`, version-1 case and `CASE_OPENED` event in the same transaction as its scoped retry record. `GET /api/cases/{id}` returns current state/version and the immutable opening event.
- Enforce one case per invoice. Same-key retries and new-key/same-invoice requests return the original opening outcome without a second event, including calls from another active credential of the same merchant. A conflicting key used for another invoice rolls back the losing case/event/record.
- Preserve original opening actor/outcome independently of later case state. Event payload contains only invoice ID/hash and policy ID, with separate canonical payload/header hashes, sequence 1, and a null previous hash. Reject unneeded payload fields and timezone-free event timestamps.
- Migration `0004` rejects duplicate historical invoice cases with a remediation report instead of deleting data. Preserve legacy hashes and null payload/version fields; do not invent policy or audit history. Reject destructive downgrade when workflow evidence exists, including a concurrent in-flight creator.
- Reuse invoice transaction/credential/key/error safeguards and retain invoice-before-case lock ordering. Recheck expiry after lock waits. Unknown/foreign IDs return 404; legacy context returns 409; errors do not disclose database internals.

### Recorded validation

Linux, Python 3.14.7, Rust 1.99.0, and disposable PostgreSQL 17 with isolated test schemas:

```text
make test: 12 Rust tests passed; 95 Python tests passed
Final PostgreSQL suite: 70 passed (including invoice and case regressions)
make lint: Rust formatting/Clippy and Python lint/formatting passed
make poc: original receipt recovery, tamper rejection, and offline balances preserved
Generated-schema consistency, documentation links, and git diff --check: passed
```

Independent review reproduced a concurrent downgrade that could discard newly committed audit payloads. A deterministic two-connection regression failed before the fix and passed after request/case/event locks were acquired before the guard. Follow-up review found no remaining blockers. Additional tests cover historical data preservation, key conflicts, new credentials, immutable records, expiry during invoice locks, and complete rollback after commit failure. The existing Starlette/httpx warning remains.

`CaseOpenedV1` and `CaseDetailV1` are deliberately limited to creation/current state and the opening event. They are not the full `CaseReportV1`; case listing, claims/evidence, later event writers, verification, and resolution remain pending. See [case API behavior and boundaries](cases.md).

## Item 05 — encrypted evidence submission and metadata

Implemented on October 11, 2026, over baseline `ab9ac73`, in separately published contract, crypto, migration, audit, service, API, review-fix, regression, schema, and documentation increments.

- Merchant-only `POST /api/cases/{id}/evidence` stores optional receipt/raw-tx strings exactly as supplied. `GET /api/cases/{id}/evidence/{evidence_id}` returns metadata only. Internal authorized decryption is prepared for the next verification service; no public plaintext route is added.
- Use locked `cryptography` 50.0.2 AES-256-GCM with an external base64 32-byte key, fresh random 96-bit nonce, full tag, and associated data binding merchant/case/evidence/key/version. Validate ciphertext and exact payload/component hashes on read; missing/wrong keys fail closed.
- Migration `0005` preserves legacy evidence without inventing encryption/ownership. Enforce same-owner/case retry references, unique key-ID/nonce pairs, and immutable metadata/content/retry records. Retaining ciphertext reservations avoids nonce reuse through deletion; purge and rotation tooling remain future work.
- Store a server-bound merchant processing acknowledgement, source labels, disclosure version, actor/time, and forced-false reviewer sharing. Source labels are assertions, including `public_fixture`; they do not establish provenance, chain status, or customer consent.
- Ciphertext, metadata, request outcome, case version/state, and `EVIDENCE_SUBMITTED` event commit together. Serialize on invoice then refreshed case locks, validate the entire known event chain, and reauthorize after waits. Same-key retries add nothing; a new key intentionally records a new submission.
- Empty/missing components remain honest stored input. For OPEN/AWAITING cases, incomplete input gives AWAITING_EVIDENCE and complete input returns OPEN pending verification; UNDER_REVIEW remains unchanged. New terminal-case submissions are blocked while completed retries remain readable.
- Readiness includes encryption configuration and new uploads fail without a valid key. Metadata remains readable without decryption. Application encryption covers the bundle body, not invoice or metadata fields.

### Recorded validation

Linux, Python 3.14.7, Rust 1.99.0, disposable PostgreSQL 17, and an isolated schema per database test:

```text
make test: 12 Rust tests; 115 Python tests passed
make test-db: 89 PostgreSQL tests passed
make lint: Rust formatting/Clippy and Python lint/formatting passed
make poc: original receipt recovery, tamper rejection, and offline balances preserved
Schema generation, documentation links, and git diff --check: passed
```

Tests cover exact-byte round trips, associated-data mismatch, tampered ciphertext, key failure, source/acknowledgement bounds, nonce collision/reservation, cross-merchant/case access, revocation during decryption, concurrent version/event progression, corrupted audit history, commit rollback, and downgrade races. Full-suite integration exposed a cross-revision lock-order conflict: migration 0005 now waits for both evidence and case creators before locking their shared tables; the existing case concurrency regression was generalized to that earlier serialization point. The final full suite passed afterward.

Independent security/code review found a malformed audit-reference error path; a failing regression reproduced it and strict reference validation fixed it. Follow-up reviews found no remaining blockers, including the cross-revision lock ordering. The existing Starlette/httpx warning remains. Public historical fixtures and synthetic data were used; no real customer keys or evidence were provisioned.

See [evidence API/key guide](evidence.md). This completes storage/submission, not persisted verification, customer/reviewer consent, or release readiness. Keep historical encryption keys securely; single-key configuration is not a completed rotation solution.

## Item 06 — persisted verification and initial offline reports

Implemented on October 11, 2026, over baseline `c59ee0a`, in separately published contract, evaluation, migration, shared-reader, audit, service, report, HTTP, review-fix, regression, schema, and documentation increments.

- Merchant-only verification accepts an owned evidence reference, authorizes/decrypts its exact stored bundle, and runs the real Rust adapter outside database locks. Persist completed valid, invalid, missing, unsupported, unavailable, and error outcomes honestly.
- Atomically record attempt, explicit offline observation, immutable evaluation inputs/result, audit event, scoped retry outcome, and case state/version. Same-key replay returns its original outcome; a new key records a new attempt. No allocation or business approval is written.
- Initial merchant reports read one repeatable-read snapshot, preserve historical evaluations, and calculate current balances from authoritative allocations. Project only the latest or selected owned candidate. Foreign-output conflicts disclose no foreign invoice IDs/amounts.
- Migration `0006` preserves legacy rows, adds scoped references and immutable observation/evaluation/retry records, and refuses destructive populated rollback after serializing with active writers. Old case-detail and receipt-result contracts remain compatible.
- Publish verify/attempt/report schemas and document derived memo/receiver disclosure: original evidence stays encrypted, but recovered fields and evaluation snapshots are outside application encryption. Customer/reviewer grants and authorized exports remain pending.

### Recorded validation

Linux, Python 3.14.7, Rust 1.99.0, and disposable PostgreSQL 17 with an isolated schema per database test:

```text
make test: 12 Rust tests; 125 Python tests passed
make test-db: 111 PostgreSQL tests passed
make lint: Rust formatting/Clippy and Python lint/formatting passed
make poc: real fixture recovery, tamper rejection, and offline balances preserved
```

Tests cover the real HTTP invoice-to-report path, wrong-owner/case access, revocation during verification, missing/tampered/unsupported evidence, unavailable binaries, temporary-storage errors, replay integrity, concurrent requests, atomic rollback, consistent report reads, foreign-allocation redaction, legacy preservation, and cross-revision downgrade races. An existing evidence downgrade test now recognizes its serialization lock anywhere in the expanded lock list; no old migration was changed.

Independent review reproduced two defects with failing regressions: temporary-file failures escaped instead of becoming stored ERROR outcomes, and replay did not verify an event's payload/header hashes. Both were fixed and follow-up review found no remaining blockers. The full suite passed afterward. The existing Starlette/httpx deprecation warning remains; no live chain confirmation or customer evidence was used.

See [verification API and report guide](verification.md). The core invoice → case → encrypted evidence → verification → initial report path is connected; case listing, claim writers, and the complete consent/access workflow remain unfinished.

## Item 07 — merchant decisions and atomic allocation

Implemented on October 11, 2026, over baseline `ab141ce`, in separately pushed contracts, policy evaluation, migration, observations, transaction service, reports, HTTP, safety tests, demo, schema, and documentation increments.

- Add merchant-only `POST /api/cases/{id}/resolve` with four typed actions, required reason, reviewed case version, and scoped idempotency key. Approval/rejection requires a same-case verification; actor, amount, identity, and chain trust cannot be supplied by callers.
- Preserve immutable policy/initial evaluator version `0.1.0`; add decision evaluator `0.2.0` with explicit source authorization, transaction binding, confirmation count, and post-lock freshness gates. Unsupported stored selectors fail closed; no historical snapshot is rewritten.
- Record a fresh immutable observation outside decision locks. ASGI composes only the offline observer and default-deny source policy. Simulated observation and permissive policy exist only in isolated test/demo composition, with no public toggle.
- Lock invoice then case, reauthorize, return completed semantic/key retries before stale/terminal checks, and evaluate current balances. Atomically persist decision evaluation, resolution, full-output allocation, case state/version, event, and retry outcome. A uniqueness loser rolls back all business records before returning same-invoice replay or an opaque foreign conflict.
- Extend reports with separate decision observations/evaluations/outcomes, retaining initial verifier history and current balance arithmetic. Reports explicitly identify simulated decisions. Legacy resolutions remain assertion views without invented decision context.
- Migration `0007` preserves legacy resolution/allocation rows, adds scoped references and immutable history, and blocks populated rollback after serializing with active writers. A failed approval's diagnostic observation is also protected from downgrade.
- Add a disposable-schema demo through the normal application services: real historical receipt recovery, blocked offline approval, labeled simulated partial approval, retry, second-invoice conflict, and tampered-receipt rejection. The script removes its schema and prints only safe trace metadata.

### Recorded validation

Linux, Python 3.14.7, Rust 1.99.0, disposable PostgreSQL 17, isolated test schemas:

```text
make test: 12 Rust tests; 134 Python tests passed
make test-db: 141 PostgreSQL tests passed
make lint: Rust formatting/Clippy and Python lint/formatting passed
make poc: historical recovery, tamper rejection, and offline balances unchanged
Isolated resolution demo: passed as part of the PostgreSQL suite
```

Safety tests prove same-output/same-invoice concurrent replay, one winner across two invoices, fresh review for concurrent different outputs, no overpayment after refresh, synthetic 600,000 + 400,000 aggregation, post-lock observation expiry, revocation during refresh, foreign/wrong-case rejection, terminal replay, event/commit rollback, immutable records, corrupted outcome/evaluation/observation rejection, legacy preservation, and downgrade serialization. Public historical receipt recovery and synthetic accounting/source inputs are explicitly distinguished.

Independent review found no blockers and independently ran 28 focused tests; additional migration, aggregation, and linkage-corruption tests passed afterward, followed by the complete final suite. The existing Starlette/httpx deprecation warning remains. No live chain inclusion, real-customer onboarding, or release-complete credit path is claimed.

See [merchant decisions and isolated demo](resolutions.md). M2's first backend slice is now demonstrated with simulated confirmation; the deployed app permits noncredit decisions but continues to block approval while offline.

## Item 08 — trusted chain adapter and review after loss of inclusion

Implemented October 11, 2026, over `67f2b20`, with separately pushed adapter/contracts, workflow/migration, regression, and documentation increments. No Vue files were added.

- Compose the offline default or an operator-configured read-only Zebra observer. Validate network, transaction ID/raw-byte hash, source synchronization and tip age, containing block, confirmation count, and a stable tip across the lookup. Bound HTTP work and response bytes; preserve sanitized provenance with an advertised node version, never credentials or receipt content.
- Version new RPC observations as `decision-observation-v2` while preserving all existing observation-v1 and historical evaluation hashes. Simulated sources remain limited to test/demo composition.
- Add merchant-only, idempotent `POST /api/cases/{id}/chain-observations`, including refresh after closure. Authorize before and after external work; serialize persistence with case mutations. A failed retry write rolls back the observation too. Approval independently refreshes each new candidate and enforces existing policy after lock waits.
- Keep approved balances/history intact after later observed mempool/side-chain placement. Surface a report review finding and block additional credit in that case; an outage cannot erase the finding. A later confirmed observation can restore inclusion status. No automatic reversal or background monitoring was added.
- Migration `0008` adds immutable scoped refresh retries and refuses downgrade when RPC history would become unreadable. Older downgrade-race tests now detect the common credential serialization lock at the new head, retaining their in-flight history assertions.
- Document configuration, provider disclosure, wire response assumptions, and the real-node validation procedure in [chain.md](chain.md). Compose forwards the optional settings.

### Validation and remaining gate

Native checks use Python 3.14.7, Rust 1.99.0, and disposable PostgreSQL 18.6 schemas. The real fixture POC remains offline. Synthetic RPC responses test confirmed/mempool/side-chain placement, missing transactions, malformed data, wrong network/raw bytes, insufficient confirmations, timeouts, stale tips, changing tips, response limits, endpoint restrictions, spoofed fields, ownership, revocation, concurrent retry, rollback, and history preservation.

Final local validation:

```text
make test: 12 Rust tests; 175 Python tests passed
make test-db: 151 PostgreSQL tests passed
make lint: Rust formatting/Clippy and Python lint/formatting passed
make poc: historical recovery, tamper rejection, and offline balances preserved
Generated contracts, local documentation links, git diff --check: passed
docker compose config --quiet: passed (container runtime not exercised)
```

The existing Starlette/httpx deprecation warning remains. Final review added regressions ensuring insufficient re-inclusion does not clear a chain-review flag, unknown observation formats fail closed, and a failed refresh retry write rolls back its observation.

The user confirmed **no trusted endpoint is available**. Actual node version/capabilities, a live historical transaction observation, and the merchant approval trace remain pending. M3's live release gate is incomplete; this implementation is not evidence of live chain inclusion.

## Next small item

Continue customer/reviewer scoped grants and consent, browser session exchange, case listing and claim writers, then authorized replay packets. Vue stays deferred. Retention/rotation and deployment/restore rehearsal also remain pending. See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for milestone order and [chain.md](chain.md) for the independent live validation gate.


## Frontend handoff integration — PR #12

Reviewed October 11, 2026, after PR #11 established the four-person assignment board. The contributor supplied a Vue 3/TypeScript/Tailwind app with landing, demo cases, merchant credential connection, evidence submission, decisions, and printable merchant reports. This is an initial frontend implementation, not completed customer/reviewer access or release acceptance.

Integration review found a TypeScript build error, invalid verification references on noncredit decisions, approval incorrectly gated by the always-false offline eligibility field, and omitted refreshed chain observations/review warnings. Focused fixes preserve server authority, correct action payloads, display latest observation history and chain-review warnings, and leave simulated partial payments under review. Report download is labeled as report JSON rather than a replay packet; live submission is explicitly merchant-only.

Validation: clean locked dependency installation, four workflow regression tests, type checking and production build passed. The production build's case and report routes were opened successfully in the local browser. Independent source review confirmed the reported blockers were resolved. Added a separate web CI job; backend CI continues to run its full suite. This does not claim browser end-to-end testing against a live chain source.

Remaining: customer/reviewer grants and sessions, API case listing and claim writers, full packet/replay, same-origin deployment integration, and complete M6 browser acceptance. M3 live-node validation remains pending because no trusted endpoint has been provided.

## Item 09 — merchant case listing (M4.3)

Implemented October 11, 2026, as Person 3 on `feat/m4-case-listing`, starting from `2de8150` after checking remote branches and open PRs. The branch was published before implementation; contracts/cursors and endpoint/database coverage were committed and pushed separately. The preceding entries remain historical records.

- Add merchant-only `GET /api/cases` returning versioned summary pages, optional exact state filtering, and limits of 1–100 (default 50). Order by creation time descending with a descending UUID tie-breaker and fetch at most one extra row to determine continuation.
- Bind versioned cursors to merchant/filter, independently verify anchor ownership, and recheck credentials before reads and before returning results. Missing/foreign/forged positions fail without disclosing foreign case existence. Pagination uses current state, with documented behavior for new inserts and state changes.
- Preserve creation, detail and report contracts. Historical rows expose summary metadata only; unsupported history still fails on existing detail/report routes. No grants, sessions, claims, frontend code, schema migrations or shared authorization changes are included.
- Publish query/list schemas and the [Person 4 API handoff](cases.md#list-merchant-cases), and update the assignment/status documents without marking M4 or M6 complete.

### Recorded local validation

macOS arm64, Python 3.12.14, Rust 1.99.0, uv 0.13.0, disposable PostgreSQL 17.11 on loopback with a separate schema per test:

```text
make test: 12 Rust tests; 191 Python tests passed
make test-db: 165 PostgreSQL tests passed
make lint: Rust formatting/Clippy and Python lint/formatting passed
make schema: published contracts regenerated
make poc: historical recovery and tamper rejection passed; chain remains UNAVAILABLE
Focused M4.3: 16 contract/cursor tests; 14 PostgreSQL API/service tests passed
```

The first native test run hit five timeouts in unchanged subprocess tests using `/usr/bin/python3`; the focused 20-test subprocess suite and complete `make test` subsequently passed without source changes. The existing Starlette/httpx deprecation warning remains. Pagination coverage deliberately makes timestamp and UUID ordering differ, includes tied timestamps, and tests all states, empty pages, merchant isolation, forged/foreign/missing anchors, rotation/revocation/expiry, expiry during a read, concurrent newer inserts, changed anchor state, legacy metadata, and real invoice/case creation. Synthetic legacy rows exercise listing only and make no cryptographic claims.

Local acceptance is recorded here; completion still requires the feature PR's final review, CI and merge under CONTRIBUTING.md. Person 4 owns dashboard integration. Person 3's customer submissions depend on M4.2; M3.1 still requires a trusted endpoint, and full release acceptance remains incomplete.

## Item 10 — shared access foundation (M4.0)

Implemented over `20a810a` on the published `feat/m4-access-foundation` branch. Shared case-grant/customer/reviewer actor contracts, transaction-time scope checks, session linkage/expiry checks, and migration `0009` prepare the grant/session and submission/report services. Existing merchant bearer behavior and historical hashes/ciphertext remain unchanged. No grant/session HTTP lifecycle or customer/reviewer data route is introduced in this increment.

New persistence retains grant/session identity and scope with revoke-only mutation, immutable consent/selections/retries, and nullable legacy-safe customer attribution. Review identified a NULL-owner composite-FK bypass; a failing regression reproduced it and explicit attributed-owner checks closed it. Follow-up review found no blockers. The new downgrade lock statement was formatted consistently with existing concurrent-writer test synchronization; no old migration was rewritten.

Final local validation (Linux, Python 3.14.7, Rust 1.99.0, disposable PostgreSQL 17): 12 Rust, 192 Python, and 173 PostgreSQL tests passed; lint/format/Clippy and POC passed. Tests cover role/case isolation, revocation, session linkage, underlying expiry after a session-lock wait, customer attribution without fake merchant credentials, migration metadata agreement, encrypted evidence preservation, and populated rollback refusal. Existing Starlette/httpx deprecation warning remains.

Contracts and consumer guidance are in [access.md](access.md). Next Person 1 tasks are M4.1 grant lifecycle and M4.2 browser sessions; Person 2's projections and Person 3's submission writers must consume this foundation without treating client-supplied contexts as authority.

## Item 11 — case grant lifecycle (M4.1)

Implemented over `87adfe3` after M4.0 merged. Merchant-only create/list/revoke endpoints issue case-scoped customer/reviewer grants, preserve explicit report/evidence/export scope, and require actual sharing consent for selected evidence. Grant codes have 256 random bits, are stored only as digests, and are returned once after commit; creation replay and metadata never redisclose the code. Case locking serializes concurrent retry creation, and revocation preserves its original timestamp. No customer/reviewer data route or browser session exchange is enabled in this increment.

Final local validation (Linux, Python 3.14.7, Rust 1.99.0, disposable PostgreSQL 17): 12 Rust, 193 Python, and 180 PostgreSQL tests passed; lint/format/Clippy, POC, and schema generation passed. Focused tests cover lifetime/scope bounds, secret-free repr/storage/replay, concurrent single disclosure, consent selection, foreign actor/case denial, changed-body retry conflict, commit rollback, expiry, revocation, and HTTP metadata/revoke behavior. Independent review found no blockers; the existing Starlette/httpx warning remains.

See [grants.md](grants.md) for API examples and lost-response handling. Next: M4.2 secure browser sessions; M4.4 consent/submission writers and M4.5 report projections remain separate owners' tasks.

## Item 12 — secure browser sessions (M4.2)

Implemented over `ace58f3` after M4.1 merged. HTTPS code exchange, current session scope, and logout use host-only Secure cookies, HttpOnly session secrets, SameSite=Strict, exact configured Origin checks, and a session-bound CSRF cookie/header for unsafe cookie-authenticated requests. Stored session/CSRF values are SHA-256 digests; issuance returns cookies only after commit. Sessions expire within eight hours and never outlive the underlying credential/grant. Existing merchant bearer authentication retains its prior behavior, including missing-credential error/challenge format.

Shared request authentication derives merchant/customer/reviewer principals from persisted access. Existing merchant data/mutation routes reject grant sessions; customer submission and reviewer projections remain M4.4/M4.5 tasks. Merchant workflow services recheck session and underlying access inside their transactions, including after external work. No frontend login screen or public deployment was added.

Final local validation (Linux, Python 3.14.7, Rust 1.99.0, disposable PostgreSQL 17): 12 Rust, 195 Python, and 190 PostgreSQL tests passed; lint/format/Clippy, POC, schema generation and documentation links passed. Tests cover hashed secret storage, bounded lifetimes, code validation, secure cookie attributes, trusted-Origin checks, session-bound CSRF, bearer precedence, HTTP refusal, parent revocation, logout, session expiry, transaction rollback, and session revocation during invoice normalization. HTTP cookie expiry required explicit UTC normalization; a full-suite regression also restored the legacy Bearer challenge. Independent review found no blockers. Existing Starlette/httpx deprecation warning remains.

Compose YAML parsed and includes browser-origin forwarding. The local Docker installation has no Compose subcommand, so Compose CLI/runtime validation was not available; this is not deployment evidence. HTTPS browser/proxy behavior and the frontend cookie flow remain deployment/browser acceptance work.

See [sessions.md](sessions.md) for Person 4's cookie/CSRF contract and [access.md](access.md) for Person 2/3's transaction/disclosure boundaries. Person 1's M4.0/M4.1/M4.2 backend implementation is complete subject to this PR's integration; M4 as a whole still needs customer submissions and scoped reports.

## Item 13 — M7.1 backend deployment preparation

Implemented October 12, 2026, as Person 3 on `feat/m7-deployment-controls`, based on `87adfe3` after M4.0 merged. The branch was published before editing, with separately pushed application-boundary and runtime/acceptance increments. P1's separately developed M4.1/M4.2 then merged, and this branch integrated main `3eef944`; shared auth/schema and frontend source/build configuration were not edited.

The optional deployment entry point reuses the current backend, applies forward migrations, serves Person 4's built Vue output, checks the public host and trusted TLS proxy, and always disables public POC/documentation routes. Startup requires a built frontend. Runtime logging excludes raw messages, request/SQL data and tracebacks; migration output is private. Final review disabled PostgreSQL container log retention because database error details can contain row contents even with statement logging off; the rehearsal inspects this driver setting. Existing development entry points retain their behavior.

The standalone Compose composition adds certificate-backed nginx ingress, fixed/chunked request limits, per-client rate/connection limits, private API/database ports, mounted secrets, non-root/read-only API and ingress containers, explicit CPU/memory/PID budgets and bounded temporary storage. It preserves packaged-head/verifier/key readiness and independent chain-source behavior. The [deployment guide](deployment.md) documents operator configuration and TLS session configuration and remaining frontend integration.

### Recorded validation

macOS arm64, Python 3.12.14, Rust 1.99.0, disposable PostgreSQL 17.11 schemas, and a separate Colima Linux/arm64 Docker 29.5.2 daemon with Compose 5.6.0:

```text
make test: 12 Rust tests; 214 Python tests passed (19 new deployment boundary checks)
make test-db: 190 PostgreSQL tests passed
make lint: Rust formatting/Clippy and Python lint/formatting passed
Actual Docker/Compose rehearsal: all ten acceptance groups passed
```

The session integration was validated and committed as `12e560b`; the final rehearsal including the database logging fix completed at 2026-10-11T16:49:30.466172+00:00 (October 12 local time). The container rehearsal used the real built frontend and verifier, fresh migrations through `0009`, disposable secrets/data and a short-lived localhost certificate verified against its explicit trust anchor. It passed HTTPS/redirect checks, SPA/asset/API separation, disabled POC/docs, actual TLS session exchange/secure-cookie scope/restoration/Origin/CSRF/logout/parent revocation, fixed/chunked oversized-body rejection, rate limiting despite spoofed forwarded headers, inspected CPU/memory/PID/non-root/read-only/capability settings, database-outage readiness/recovery, and secret-canary checks against container logs. All test containers, networks and data volumes were removed by the harness. The [CI workflow](../.github/workflows/deployment.yml) repeats this runtime rehearsal.

The initial runtime checks exposed malformed tmpfs YAML and nginx temporary/template paths incompatible with a read-only root; the final configuration fixes those issues and waits for ingress readiness. Five unchanged native subprocess tests initially timed out under the macOS system Python; the complete suite passed outside the sandbox after the container build, without source changes to those tests. The existing Starlette/httpx deprecation warning remains.

This is the completed backend-preparation slice, subject to its PR review/CI/merge gate. **M7.1 remains incomplete:** Person 4 must provide actual-backend browser workflow/accessibility evidence. No public deployment, live RPC observation, real-customer pilot, backup/restore acceptance, or full release completion is claimed. Earlier development entries remain historical evidence.

## Item 14 — customer claims and encrypted evidence (M4.4)

Implemented October 12, 2026 as Person 3 from main `0ff3b31` on the published `feat/m4-customer-submissions` branch. Remote branches and PRs were checked before claiming the task. The branch was published before editing, then contracts and transactional implementation were committed/pushed as separate increments. The work consumes P1's existing access/session/consent/retry persistence; no database migration, parallel identity model, frontend implementation or reviewer projection was introduced.

Scoped merchant/customer claim writes derive actor and role from persisted access. Claims record a hash-bound disclosure/consent event; v2 evidence records the actor, exact encrypted input, sharing-consent row, optional same-case claim reference, audit event and safe retry outcome atomically. Sharing defaults false. Customer evidence requires the explicit v2 disclosure; claim/evidence acknowledgements contain only acceptance, operation, resource ID and time. Customer reads and merchant verification/decision/grant actions remain denied. Existing merchant evidence v1 requests, ciphertext, hashes, metadata and retries retain their format.

The writers serialize case versions/events, recheck permission after external encryption and lock waits, reject new terminal-case writes and keep completed retries authorization-bound. Merchant readers/real verification accept mixed evidence/event versions. Review added a claim-history check so changing an attributed claim's note outside the writer cannot silently alter the merchant report; a database regression proves the 409 response. Claim text remains in the existing plaintext database columns, with disclosure and retention boundaries documented explicitly.

### Recorded validation

Local macOS arm64, Python 3.12.14, Rust 1.99.0 and isolated PostgreSQL 17.11: the full initial PostgreSQL suite passed 209 tests; the subsequent integrity-fix run passed all 25 affected submission/report tests (20 M4.4 PostgreSQL/HTTP scenarios). All 17 new contract/audit tests passed. Lint/format/Clippy, schema generation and documentation/diff checks passed. Initial native full-unit runs hit five, then one intermittent 0.2-second timeout in unchanged system-Python subprocess tests; their focused 20-test suite passed. No timeout threshold or unrelated test was changed.

Linux branch CI for `3032398` passed the complete `make test`, `make test-db`, `make lint` and `make poc` commands, frontend tests/build, and the actual TLS container rehearsal. Final-head CI remains the PR integration gate. The existing Starlette/httpx deprecation warning remains.

The new scenarios cover explicit/default consent, honest credential/grant attribution, byte preservation, minimal HTTP responses and CSRF, customer/reviewer/foreign-merchant isolation, claim linking, session-renewal retries, concurrent same/different keys, actor/operation/version retry scoping, rollback at deferred commit, terminal cases, revocation during encryption, expiry during a case-lock wait, reviewer evidence consent selection, audit tampering, and real merchant verification/report compatibility.

See [customer-submissions.md](customer-submissions.md) for P2/P4 contracts and exact disclosures. This is M4.4 implementation/validation evidence, not a merged-feature or full-M4 completion claim. M4.5 reviewer projections, M5 replay/export, P4 browser acceptance, live endpoint validation and full release/restore remain their separate gates. Earlier development records are preserved as historical evidence.

## Item 15 — M7.2 backend recovery rehearsal

Implemented October 12, 2026 as Person 3, from main `efa6869` after M4.4 merged in PR #18. No remote feature branches or open PRs overlapped when checked. `test/m7-release-rehearsal` was published before implementation. Forward-migration evidence and runtime recovery were committed/pushed as separate coherent increments (`0d0af4b`, `4eb8d7f`); documentation follows separately. Earlier development entries remain historical evidence.

The [recovery guide](recovery.md) maps all A-01–A-15 acceptance rows to existing/backend evidence and remaining release gates. The current board/README/PRD now record M4.4 as merged and M4.5 as ready for Person 2. This increment introduces no production API, authentication, schema, verifier or frontend changes.

### Recorded validation

At **2026-10-12T00:19:23Z**, `.venv/bin/python scripts/check_deployment.py --recovery --keep-on-failure` passed all **19 actual-container acceptance groups**: the ten M7.1 TLS controls plus nine M7.2 groups. Host: macOS 27.0.1 arm64, Python 3.12.14, Docker 29.5.2; application image: Python 3.14 with the packaged real Rust verifier and PostgreSQL 17. The result records revision `0d0af4b` with `working_tree_changes=true`; that tested runtime implementation was subsequently committed as `4eb8d7f`. Clean revision-specific Linux evidence is produced by the deployment CI artifact; a working-tree run is not presented as a clean-commit run.

The rehearsal upgraded a populated synthetic schema from `0008` to packaged head `0009`, preserved original columns and encrypted bytes across nine legacy tables, retained a 100,000-zatoshi allocation without inventing attribution, repeated the forward migration, and removed the schema. The current workflow separately used the public receipt and real verifier, confirmed production offline approval denial, and seeded one explicitly `SIMULATED` allocation through the normal resolution service in an isolated test process.

After API SIGKILL, database restart, and an encrypted full-database dump/restore into a separate empty database, exact claim/evidence/approval retries reproduced their prior outcomes. Every application-table row digest matched the checkpoint; 100,000 credited and 100,000 outstanding remained unchanged. Both evidence versions decrypted with the preserved external evidence key, wrong/missing evidence keys failed, and wrong backup keys/tampered archives were rejected before restoration. Duplicate allocation, invalid foreign reference and immutable invoice edits failed after restore. Restored customer role limits and grant revocation remained effective; credential/session/claim/URL canaries did not enter retained runtime logs. The harness removed its test containers, networks, volume and private files after success.

`make test-db` passed **211 tests** against isolated local PostgreSQL 17.11. The new archive suite passed **six tests**, and the new forward-migration regression passed against real PostgreSQL. `make lint` (Rust format/Clippy and Python lint/format), documentation links and `git diff --check` passed. Native `make test` passed all **12 Rust tests** and 232 Python tests but hit the same five unchanged 0.2-second system-Python subprocess timeouts recorded in earlier work; a focused run passed 19/20 with one timeout. No unrelated timeout or production code was changed. Linux CI remains required for the complete Python suite. The existing Starlette/httpx deprecation warning remains.

Linux CI on `4eb8d7f` subsequently passed all **12 Rust, 237 Python and 211 PostgreSQL tests**, lint, POC, frontend tests/build, and the full container recovery rehearsal. Final review disabled networking and Docker logging for the temporary archive helpers so decrypted stdout cannot enter daemon logs. The hardened full local rehearsal passed all **19 groups** again at **2026-10-12T00:23:05Z**, from `aee7e5d` plus the recorded working-tree hardening changes; final-head CI remains the integration gate.

The first container attempt correctly rejected a wrong evidence key but exposed a harness exception-type mismatch; the assertion now checks the service's wrapped error codes and the full rehearsal passed afterward. The initial command used the system Python 3.9, which cannot run the existing harness; the documented command uses the repository environment. Neither failed attempt is counted as passing evidence.

**Scope remains backend preparation.** Client response loss is modeled after a committed result, not every crash location. The bounded archive helper is not a production backup/retention/PITR service; external key custody, volume encryption and recovery of writes after the selected backup remain operator responsibilities. M3.1 live validation, P2 scoped reports/export/replay, P4 actual-backend browser results/screenshots, and the complete release/demo evidence remain outstanding. Final review, CI and PR merge are still required for this increment; full M7.2 is not complete.

## Item 16 — scoped reviewer reports (M4.5)

Person 2 implementation by Codex on `feat/m4-scoped-reports`, based on main
`38d9422`. The branch was published before implementation and the first tested
increment was pushed as `6900cc9`. Report and evidence reads consume the merged
P1 authorization and P3 consent handoffs. Explicit reviewer models omit private
nested snapshots, actor identities and unselected/unconsented records; merchant
reports retain their contract. Exact-component evidence reads reauthorize after
decryption. No frontend, migration, export or live RPC work is included.

Local Linux x86_64, Python 3.14.7, Rust 1.99.0 and isolated PostgreSQL 18.6 schemas:
`make lint` passed; `make test` passed all 12 Rust and 237 Python tests. The first
28 focused report/submission scenarios passed. The subsequent foreign-allocation
and decision-disclosure check passed (two selected cases including the foreign
merchant HTTP role). Test development corrected fixture assumptions about memo
binding, the refresh route and a synthetic fixture dictionary key; none required
weakening production permissions. The existing Starlette/httpx deprecation warning
remains. Full database and final-head CI results are recorded below before merge.

See [scoped-reports.md](scoped-reports.md) for P4/M5 integration, the field matrix,
original-content sensitivity and projection/replay limits. Live-chain validation
and browser acceptance remain pending independently.

The full initial database run passed 218 tests and found one pre-M4.5 session
assertion still treating every reviewer report as merchant-only. That regression
now checks merchant-only case detail and separately asserts the newly permitted
case-only reviewer report while retaining customer denial.

At 2026-10-12T03:29Z, all 15 affected session/reviewer PostgreSQL scenarios passed
on the corrected working tree. Final lint/format/schema and diff checks passed.
CI on the first increment reproduced the same obsolete session assertion; the
final branch includes its scoped-access correction and awaits fresh CI.

M4.5 final revision `f1ae85c` passed all **220 PostgreSQL**, 237 Python and 12 Rust
tests, lint, frontend CI and both actual-container CI runs. PR #20 merged as
`410571b`; its branch was removed after ancestry verification.

## Item 17 — packet contract (M5.0)

Person 2, `feat/m5-packet-contract`, based on merged main `410571b`. Published the
branch before implementation; contract/fixtures committed as `9154f70`. At
2026-10-12T03:37Z on Linux x86_64/Python 3.14.7/Rust 1.99.0, all **13 new contract
checks**, **250 Python unit tests**, **12 Rust tests**, and `make lint` passed.
Schema generation, deterministic fixture regeneration and diff checks passed.
There are no database or permission mutations in this increment; M4.5's full
220-test PostgreSQL run is recorded above. Final CI remains required.

The [packet contract](packets.md) defines exact base64 UTF-8 originals, separate
original/decoded transaction hash bases, unchanged historical records, explicit
complete/limited scope and external assertion limits. The fixtures include v1
and v2 submission/events and both decision observation schemas. Simulated
approval and synthetic unavailable RPC-shaped history are explicitly labeled;
no live endpoint was queried.

**Publishing block:** GitHub rejected the first implementation push with HTTP
403, “Your account is suspended.” Read-only PR listing failed with the same
account suspension. The local commit is intact; the remote branch still points
to its pre-implementation base. No M5 PR/CI/merge is claimed. Remaining P2 work
continues on local dependent task branches so implementation and tests remain
reviewable. Once account access returns, publish and integrate M5.0, M5.1 and
M5.2 in order through passing CI and merge-commit PRs; do not push to main.

## Item 18 — offline replay (M5.1)

Person 2 continued on local `feat/m5-replay-case`, based on validated M5.0 commit
`8f02391`; GitHub account suspension prevents publishing or merging prerequisites.
The core implementation is committed as `0ea6971`. No GitHub retry will be made
until the user reports restored access. No CI/PR/merge completion is claimed.

On Linux x86_64/Python 3.14.7/Rust 1.99.0 at 2026-10-12T03:45Z, `make lint` passed,
`make test` passed **12 Rust and 269 Python tests**, including **19 new replay
scenarios**. All 32 focused packet/replay tests passed. The installed `replay-case`
entry point also reproduced the current complete fixture. The recorded actual
CLI examples return valid=0/REPRODUCED, tampered=1/FAILED, scoped=2/LIMITED,
missing-version=2/LIMITED, unsupported-version=3/UNSUPPORTED with input file hashes.

The engine verifies original components, historical hashes and relationships
before invoking the real bounded local verifier. Fixed historical dispatch
reproduces initial rules 0.1.0 and decision rules 0.2.0 using recorded time and
inputs. It distinguishes self-consistent hashes from recovered output and from
external invoice/claim/chain/allocation assertions. Missing version fields cannot
silently inherit the schema's default implementation. Packet data cannot select
executables, download code or initiate network requests. No database or credit
mutation is performed. Existing historical formats/hashes remain unchanged.

See [replay usage and limits](packets.md#offline-replay-m51) and
[recorded examples](../fixtures/packets/replay-results.json). M5.2 authorized
snapshot export is the next local task; full remote integration remains pending.

GitHub access was restored later in the same session. All three M5 branches were
published; M5.0 PR #21 passed foundation, web and actual-container checks and
merged as `fe08aef`. The earlier suspension entries describe that temporary
interruption, not a current access limitation. M5.1 continues through PR #22.

## Item 19 — authorized snapshot export (M5.2)

Person 2 implementation on `feat/m5-case-export`, initially stacked locally on
M5.1 `bbdd524` during the GitHub interruption. After access was restored, remote
branches/PRs showed no overlapping work and all task branches were published.
The first export increment was committed and pushed as `f71a9b5`; focused
permission/concurrency tests accompany it. Review and integration continue in
M5 dependency order with merge commits.

`GET /api/cases/{id}/export` uses the shared authorizer, M4.5 projections and M5.0
contract. One repeatable-read snapshot includes report state, original ciphertext,
metadata and balance/allocation inputs. Decryption occurs outside its transaction;
a fresh authorization check covers credential/grant/session expiry and revocation
plus the entire consent selection. It does not reread and mix newer report data.
Merchant packets retain complete original submissions; reviewer packets omit
private submission/claim links, actor and full audit/allocation context, identify
omissions and cannot claim full replay. Foreign conflicts remain opaque assertions.
There are no model, migration, frontend, chain-trust or credit-writer changes.

Recorded at **2026-10-12T03:52:55Z**, Linux x86_64, Python 3.14.7, Rust 1.99.0 and
isolated native PostgreSQL 18.6 schemas: `make lint` and `make test` passed all
**12 Rust and 269 Python tests**; `make test-db` passed **234 database tests**.
The 30 focused export/report/evidence tests passed. Two subsequently added
missing-versus-empty export/replay scenarios also passed, bringing export coverage
to **16 scenarios**. Those additions change tests only; final CI will cover all
236 PostgreSQL tests. The first export test run exposed an incorrect test-helper
revocation signature; correcting it made the credential revocation case pass.
The existing Starlette/httpx deprecation warning remains.

The tests prove a concurrently approved case exports either the earlier history
with zero credit or the later history with 100,000 approved zatoshis; both replay.
They also cover real v2 claim/consent history, legacy simulated approval, exact
originals, tampering, five HTTP roles, explicit export permission, case-only
limited exports, grant/credential/session revocation during decryption, expired
grants, private linked claims, foreign conflicts, byte limits and negative replay.

[Packet/export/replay usage](packets.md), [scoped report fields](scoped-reports.md),
README, PRD and TEAM_GUIDE provide the backend handoff. M3.1 still needs a trusted
live endpoint; P4 frontend/download/browser acceptance and full release gates
remain separate. Final-head CI and PR merge are required before M5.2 completion.

M5.1 final review after access restoration added a raw-transaction omission
regression: a scoped packet may retain the selected verification's decoded hash
while withholding the raw bytes, so replay reports missing input rather than a
false integrity mismatch. Both receipt and raw-byte omissions now remain LIMITED.
All 33 focused packet/replay checks pass; no full-history packet permits omitted
inputs. This correction is part of PR #22 before merge.

M5.1 final revision `cbf8c54` passed foundation, web and actual-container CI and
merged through PR #22. Its remote branch was removed only after ancestry
verification. On integrated export revision `03bafe8` (with documentation-only
working tree updates), the final local run completed by **2026-10-12T04:00:12Z**:
**12 Rust, 270 Python and 236 PostgreSQL tests passed**, plus lint, schema
regeneration, deterministic replay-output regeneration, POC and documentation
link/diff checks. This includes all 16 export and 20 replay scenarios. The only
merge conflict was two appended validation notes; both records were retained.
M7.2 backend preparation is also confirmed merged as PR #19, correcting an older
progress-board label. Export final-head CI remains its integration gate.

M5.2 integration is tracked in [PR #23](https://github.com/Kurisu-Labs/zecsolve/pull/23),
with the full final validation results and the reviewed export-only diff.


## Item 20 — M7.2 export/replay recovery integration

Implemented October 12, 2026 as Person 3 from main `640b1b1`, after P2 scoped reports, packet contracts, replay and authorized export merged in PRs #20–#23. No open PR or remote feature branch overlapped when checked. `test/m7-export-recovery` was published before implementation; the runtime rehearsal and five comparison regressions were committed/pushed as `4c47e4b` before this documentation increment. Items 01–19 are retained unchanged as historical evidence.

The existing disposable TLS/restore harness now exercises the merged HTTP report/evidence/export interfaces before interruption, after API SIGKILL/restart, after PostgreSQL restart and after encrypted fresh-database restore. Reviewer access uses real exchanged browser-session cookies. A private linked claim, nonconsented legacy evidence and a consented but unselected submission stay undisclosed. Report-only grants cannot export; anonymous/customer/revoked access is denied. A grant revoked before backup stays revoked after restore, and revoking the restored active reviewer denies new report/content/export reads.

At every checkpoint the merchant packet reproduces real output recovery and historical accounting through the installed `replay-case` CLI (`0/REPRODUCED`); selected reviewer and case-only packets return `2/LIMITED` with explicit omissions. Original receipt/transaction bytes match the fixture exactly. A one-byte change without rehashing returns `1/FAILED` at integrity validation. Replay uses the built application image and packaged Rust verifier, with no networking, database or secret mounts, a read-only root and bounded tmpfs, and Docker logging disabled. The sanitized CI artifact contains only hashes and expected statuses for these packets.

The entire exported payload remains equal across recovery after excluding only the fresh `report.generated_at` timestamp. This compares historical identities, consent/provenance projections, evidence components, allocations and audit history as well as amounts. Existing full-table row fingerprints remain equal after all reads/replays/retries. Five regression checks prove timestamp tolerance without mutating inputs, and detect changed amounts, evidence, historical hashes and omissions.

### Recorded validation

[Linux deployment/recovery CI](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38218166043) passed all **24 actual-container groups** at **2026-10-12T07:34:34.032559Z**, revision `4c47e4bf9f3c603c9ae6853c82de1fb0f207d8da`, `working_tree_changes=false`. Environment: Linux 6.17.0-1022-azure x86_64, Python 3.14.8, Docker 28.0.4, PostgreSQL 17 and the packaged real Rust verifier. Its `backend-recovery-evidence` artifact records all four export/replay checkpoints, equal per-role history hashes, unchanged database rows, correct CLI exits, tamper rejection and restored reviewer revocation. It retains `live_confirmation=false`, `release_complete=false` and the remaining live/browser/full-release gates.

[Foundation and web CI](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38218166014) passed on the same revision: Rust/Python lint, **12 Rust tests, 275 non-database Python tests and 236 PostgreSQL tests**, the offline POC, frontend tests and production build. No frontend source or build configuration, production API/auth/schema, packet contract, verifier behavior or dependency version changed in this increment.

Local macOS validation passed all **236 PostgreSQL tests**, the **five new comparison tests**, Rust format/Clippy, Python lint/format and all **12 Rust tests**. Native `make test` passed 267 Python tests and failed eight existing system-Python subprocess cases using a 0.2-second deadline (three normalizer, two process-runner and three verifier assertions timed out before their intended failure). This is the previously recorded native timeout limitation; no timeout or production behavior was altered to make it pass. The complete Linux suite above passed unchanged. The existing Starlette/httpx deprecation warning remains.

The full local container rehearsal also passed all **24 groups** at **2026-10-12T07:38:39.967846+00:00**, revision `4c47e4b` with `working_tree_changes=true` (documentation edits; runtime code matches that commit). Host: macOS-27.0.1-arm64-arm-64bit, Python 3.12.14, Docker 29.5.2. It cleaned up its containers, volumes and private rehearsal directory after success. This local run and the clean Linux CI artifact independently exercised the same four export/replay checkpoints.

Full M7.2 remains incomplete: M3.1 needs the operator's trusted RPC endpoint and live merchant approval trace; P4 owns actual-browser/download/accessibility results and screenshots; operator and team release/demo evidence remains outstanding. Public historical inputs and explicitly simulated accounting do not prove live chain inclusion or authorize a private-customer pilot. Final review, current-head CI and PR merge are still required for this integration slice.


## Item 21 — M7.2 release evidence consolidation

Person 3 started October 12, 2026 from `f2436a92e9c2f6068454e19f8f99732129223e6a`, after PR #24 merged. Remote branches and open PRs showed no overlapping work. `docs/m7-release-evidence` was published before editing. The evidence index and retained report were committed/pushed as `c1d15f4` before the status/documentation increment. Items 01–20 are preserved byte-for-byte; their earlier pending-status statements remain historical records, not current task status.

[release-evidence.md](release-evidence.md) maps every A-01–A-15 row to named backend scenarios and revision-specific successful CI evidence, with explicit live/browser/operator/team handoffs. It documents the existing offline POC, disposable-schema simulated approval/retry/conflict demo, fixture replay and deployed authorized-export/recovery commands. It distinguishes public historical receipt recovery, synthetic accounting and simulated confirmation from the missing live trace. README, PRD, assignment board and affected handoff guides now reflect PR #24's merge; no milestone is marked release-complete.

The `recovery-result.json` from GitHub run `38218166043`, artifact `11732947385`, is retained unchanged at [evidence/m7-recovery-4c47e4b.json](evidence/m7-recovery-4c47e4b.json). Retrieval verified the ZIP against GitHub's published digest and the retained JSON SHA-256 `6466446d3ff7c67976695fcc66e201e6a17923745e67ed61a3a4b363ea6a6ce9`. The source run targets clean revision `4c47e4bf9f3c603c9ae6853c82de1fb0f207d8da`, as originally recorded in Item 20. Its 24 check groups, four role/export checkpoints, stable history hashes, `live_confirmation=false` and `release_complete=false` were checked. Foundation/web run `38218166014` and container run `38218166043` were confirmed successful; their timestamps and job links are in the index. This is verification of existing evidence, not a new container or full-suite run.

### Recorded validation

On local macOS 27.0.1 arm64, Python 3.12.14 and Rust 1.99.0, command verification completed by **2026-10-12T12:09:30Z**, baseline `f2436a9` plus documentation-only working-tree changes:

- `make poc` passed with the real built verifier: 100,000-zatoshi valid recovery, tampered evidence invalid, chain unavailable, no credited balance and the expected candidate projection.
- `uv run --locked python scripts/record_replay_examples.py` reproduced all five checked-in CLI examples byte-for-byte; `git diff --exit-code -- fixtures/packets/replay-results.json` passed. The recorded exits/statuses were explicitly checked: valid 0/REPRODUCED, tampered 1/FAILED, scoped and missing-version 2/LIMITED, unsupported-version 3/UNSUPPORTED.
- Direct installed `replay-case` invocations reproduced complete-v1 and complete-v2 with exit 0/REPRODUCED; scoped returned the expected exit 2/LIMITED.
- Acceptance IDs and named test functions were checked against the repository; local documentation links/anchors, retained artifact integrity, historical-log preservation and `git diff --check` were checked for this documentation-only change.

The local commands used the existing Cargo cache in offline mode and a temporary uv cache; no RPC was configured or contacted. The database demo and full container/database/application suites were not rerun locally for this documentation slice; their attributable previous results remain E-01/E-02 in the index. Repository PR CI remains required. No production code, frontend, contracts, fixtures, dependencies or workflow configuration changed. Full M7.2 still requires the operator's live endpoint and M3.1 approval trace, P4 actual-browser evidence, and operator/team release artifacts. This consolidation slice still requires final PR review, CI and merge.


## Item 22 — M3.1 live fixture and merchant approval validation

Person 3 started October 12, 2026 from `4066ec8bf25f10372e3900bf0ba8f02bd00ccf7e`.
Remote branches and open PRs were checked before publishing
`docs/m3-live-validation`. There were no open PRs; Person 4's active
`feat/m6-frontend-integration` owns frontend implementation and also edits shared
status paragraphs. This slice changes M3 status only in those documents; preserve
both owners' updates when integrating. Items 01–21 remain byte-for-byte historical
records. The operator explicitly selected the QuickNode public documentation
endpoint and existing public receipt; no new payment or provider account was needed.

The opt-in `scripts/validate_live_chain.py` harness and repeatable procedure were
committed/pushed as `f8a594fa7364a47fd94d961054b1f88429195b90` before execution.
It invokes the ordinary authenticated FastAPI routes through an in-process
TestClient, the actual Rust verifier and the server-configured ZebraObserver.
There is no injected observer, authority function or HTTP mock. Outbound RPC uses
actual HTTPS; API ingress/TLS/browser/container acceptance is outside this run.

### Recorded live validation

The unchanged [JSON trace](evidence/m3-live-f8a594f.json) records clean `f8a594f`,
**2026-10-12T13:23:24.163901+00:00 through 13:23:30.760930+00:00**, Darwin 27.0.0
arm64, Python 3.12.14, PostgreSQL 17.11 (Homebrew), and migrations through `0009`.
The matching verifier was built with Rust 1.99.0 using `cargo build --locked
-p zecsolve-verifier`; its binary hash is retained in the trace. The command was:

```sh
uv run --locked python scripts/validate_live_chain.py --output docs/evidence/m3-live-f8a594f.json
```

The actual invocation used the installed `.venv/bin/python` from the locked
environment. `ZECSOLVE_TEST_DATABASE_URL` selected a fresh loopback-only PostgreSQL
instance on port 55439; RPC settings came from the ignored local `.env`. Source
`quicknode-public-demo`, timeout 30 seconds, tip age limit 900 seconds; no Basic
authentication. Neither database URL nor RPC URL/credentials are in the JSON.

- Real receipt recovery: `VALID`, 100,000 zatoshis; initial verification remains
  `UNAVAILABLE`/offline and has zero approved credit.
- Live node: `/Zebra:6.4.2/`, version `6040200`. All four required methods succeeded.
  Mainnet block 3,361,512 had 153,734 confirmations at tip 3,515,245; decoded raw
  bytes matched the verified transaction. Adapter synchronization, stable-tip,
  header/transaction consistency and tip-freshness checks passed.
- Anonymous refresh returned 401; authenticated refresh returned 201 and an
  identical same-key retry returned 200 with `Idempotency-Replayed: true`.
- Merchant `APPROVE_OUTPUT` returned 201 with a distinct fresh live observation,
  authorized source and `eligible_for_credit=true`. Observation age at evaluation
  was 2.600470 seconds against the 60-second policy; confirmations exceeded 10.
  Resolution `3dfad984-1cf8-446a-9eeb-25db004291b2` and all safe references are retained.
- Approval retry returned the identical decision with 200/replay header. There
  was one decision, 100,000 credited and 100,000 outstanding on the synthetic
  200,000-zatoshi invoice. No ZEC was sent. The random schema was removed and its
  absence checked; ephemeral credentials and encryption key were not retained.

Trace SHA-256:
`c7e9c885978313878a97c31a6c986f26339d9d8768b77ac27845e29d0486c2b1`.
The JSON is public-fixture/synthetic application data plus real provider
observations, not private customer data or an independent consensus proof.
`full_release_complete=false` remains explicit. See [chain.md](chain.md#recorded-live-run)
for the difference between the successful decision and the report's unchanged
initial-offline candidate projection.

### Repository validation

At the same `f8a594f` revision, `make test lint` passed outside the sandbox:
12 Rust tests, 275 non-PostgreSQL Python tests; Rust formatting/Clippy and Python
lint/formatting passed. The preceding sandboxed run had 270 Python passes and
five short-timeout subprocess failures in the existing address/process tests;
the unchanged full suite then passed outside the sandbox. Both outcomes are
recorded, and no production timeout or test was weakened. The existing
Starlette/httpx deprecation warning remains.

`python -m pytest apps/api/tests/test_rpc_workflow.py -q` passed all 10 PostgreSQL
regressions against the disposable instance. These are deterministic synthetic
RPC tests, separately from the real live run above. No application, schema,
contract, frontend or workflow configuration changed. CI remains offline and
must pass for the PR. The `f8a594f` branch [CI run](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38255318490) passed. Evidence schema/reference/hash checks, secret-field review,
243 local documentation links/anchors, historical-log preservation and
`git diff --check` passed before publication. Full release still requires P4/browser,
deployed-target/operator and team artifacts. M3.1 acceptance is demonstrated;
review, CI and merge remain the task-completion gate.

## Item 23 — M7 browser CI and release integration

**Owner:** Person 3. **Branch:** `test/m7-browser-release-integration`.
Started from clean, updated `main` at `8e8843d` after fetching remote branches and
checking open PRs. No open PR overlapped; the remaining P4 remote branch had no
commits outside main. The task branch was pushed before implementation. P4's
frontend implementation and recorded browser evidence merged in PR #26; M3.1
live validation merged in PR #27. Items 01–22 are preserved byte-for-byte.

### Integration

`scripts/browser_acceptance.py` runs P4's existing browser scenarios, rejects
failed/flaky/skipped/empty selections and focused tests, and retains only
allowlisted results. Raw diagnostics and downloaded packets stay private.
Shared CI now checks generated frontend types and runs the isolated simulated
approval/retry/conflict case. The deployment job runs the eight offline browser
scenarios through the actual built app and nginx TLS ingress, then the existing
four recovery/export checkpoints. Production auth, schema, chain policy, ingress
limits and UI behavior are unchanged. Test-only origin/request pacing and
page-readiness waits let the same P4 suite run through the real deployment.

Implementation was committed/pushed as `6044234`; actual deployment testing found
and corrected two orchestration issues in `7d4ffcf`:

- Recovery's simulated allocation already owned the globally unique public output,
  so a later browser run correctly reported zero candidate credit/conflict even
  with a new merchant. Browser scenarios now run before recovery seeds that
  allocation; no row, allocation or constraint is bypassed/deleted.
- Two immediate test checks raced the rendered Connect/page heading through the
  slower ingress. Assertions now await those visible headings before login-mode
  selection and axe analysis. No accessibility rule or scenario was disabled.

### Local execution and limits

On macOS 27.0.1 arm64, Python 3.12.14, Node 26.11.0, Playwright 1.64.0 Chromium,
Rust 1.99.0 and Docker 29.5.2/Colima with PostgreSQL 17:

- `npm test`, `npm run types:check`, `npm run build`: 8 unit tests, generated
  contract check and Vue/TypeScript production build passed.
- `make lint`: Rust fmt/Clippy and Python ruff passed. The six new report-boundary
  tests passed, including rejection of incomplete coverage and omission of raw
  diagnostics/attachments.
- `make test`: 12 Rust tests passed; native Python had 276 passes and five existing
  0.2-second subprocess timeout failures in address/process tests, also seen in
  earlier local records. These are recorded failures, not a passed local suite;
  no timeout or production code was weakened. Linux CI below is the full pass.
- The isolated simulated browser case passed at 14:32:00–14:32:07 UTC. The first
  combined run failed three browser scenarios for the ordering/readiness issues
  above. After correction, all eight nginx browser scenarios passed at
  14:37:58.515183–14:39:00.248720 UTC. The full 26-group deployment/recovery run
  completed at 14:40:39.297232 UTC. These were working-tree runs; the report records
  `working_tree_changes=true`. The disposable projects, databases and private
  diagnostics were removed afterwards.

The browser checks use generated localhost TLS with Playwright's certificate
verification disabled. Separate deployment HTTP clients validate the certificate
and hostname using an explicit trust anchor. CI uses public fixture/synthetic
application data and no live RPC; simulated confirmation remains test-only.
These checks do not constitute public deployment or full release completion.


### Linux CI and retained evidence

Clean implementation revision `7d4ffcf49a4b9348be4c2034b1a2614f2ec6fa9e` passed
all four branch CI jobs. E-07–E-09 in the [release evidence index](release-evidence.md)
link their exact jobs and preserve the two sanitized machine reports with verified
GitHub ZIP digests and retained-file hashes:

- `container-smoke`: all 26 groups, including 8 packaged-nginx browser scenarios
  and the four recovery/export checkpoints; result at 14:45:31.074549 UTC.
- `browser-simulated`: 1 explicit simulated approval/retry/conflict scenario,
  14:39:10.486977–14:39:15.673935 UTC.
- `foundation`: lint, 12 Rust + 281 non-database Python + 236 PostgreSQL tests and
  the public-fixture POC passed; the existing Starlette/httpx warning remains.
- `web`: 8 unit tests, generated contract drift check and production build passed.

The retained reports have `working_tree_changes=false`; no prior failure is
rewritten as success. The follow-up documentation corrects merged P4/M3 statuses,
indexes E-06 original P4 evidence and E-07/E-08 Linux repetitions, and keeps final
operator/team/demo/UI-screenshot requirements explicit. The recovery subreport's
legacy `remaining_gates` label is clarified as `outside_recovery_scope` in future
reports; the retained historical bytes remain unchanged. This metadata-only
change does not alter any recovery assertion. PR review, current CI and merge
remain required for task completion; no public deployment or full M7 release is
claimed.

## Item 24 — M7.2 final release bundle and demo rehearsal

**Owner:** Person 3. **Branch:** `test/m7-final-release-bundle`.
Started from clean updated main `ded49e1` (merged PR #28). Remote branches were
fetched and open PRs checked; none overlapped and the remaining P4 branch had no
commits outside main. Published the task branch before implementation. Items
01–23 and the previously retained reports remain unchanged.

### Implementation and evidence boundary

`bc0cd95` added a repeatable, asserting three-scenario release rehearsal and
shared CI artifact registration. `775ca5d` added an authorized public demo export
and verified its offline replay. Each increment was committed/pushed separately.
No production application, authorization, schema, contract, chain policy, frontend
source or browser scenario changed.

`scripts/rehearse_release.py` executes the actual POC, isolated service demo and
replay CLI. It checks exact candidate balances, blocked offline approval,
simulated partial credit, identical retry, opaque second-invoice conflict,
tampered evidence/rejection with zero credit, and temporary-schema cleanup.
Complete v1/v2, tampered, scoped, missing-version and unsupported-version packets
must produce the expected six exit/status pairs. Public fixture and license
hashes must match. Failure removes previous success output and withholds raw
child diagnostics. The source service demo optionally exports its newly created
merchant case using the existing authorization/decryption service and checks the
original receipt/transaction bytes against the public fixture. No private case ID
or evidence is accepted by this rehearsal.

CI retains the sanitized report and known public/synthetic packet as
`release-demo-evidence`. The sample contains generated actors/business history
and explicitly SIMULATED approval; no access token or encryption key is retained.
The runner replays it before publication. Separately, the existing deployed
browser/recovery job proves HTTP export authorization and exact history across
restart/restore. Service export is not mislabeled as browser/HTTP execution.

The [technical bundle](release-bundle.md), machine inventory and E-10–E-13 in the
[release index](release-evidence.md) pin candidate `775ca5d`, all fifteen
acceptance rows, exact jobs, UTC times, environments, verified artifact ZIP/member
hashes, a repeatable demo cue sheet, limitations and attribution. Follow-up
commits assemble documentation/evidence only. The historical M3.1 source is an
ancestor and its backend/migration/verifier/contracts/live-runner files have no
diff to this candidate. This is an explicit association of the existing live
result, not a fresh RPC call, new payment or live browser test.

### Validation

- Local lint/format passed. Six focused runner/demo checks passed, including
  failure/timeout/malformed child output privacy, stale-success removal, real
  three-scenario execution and authorized public export/replay.
- `make test-db` passed 237 PostgreSQL tests on a fresh PostgreSQL 17.11 instance.
  The test instance had zero remaining demo schemas and was stopped afterwards.
- `make test` passed 12 Rust tests; local Python had 280 passes and five existing
  macOS 0.2-second process/address timeout failures. This is not a local full-suite
  pass. As in prior items, production timeouts and tests were not weakened.
- The first clean runner revision `bc0cd95` passed locally at
  2026-10-12 15:22:42.267479–15:22:43.695972 UTC on macOS 27.0.1 arm64,
  Python 3.12.14, Rust 1.99.0 and PostgreSQL 17.11. That run predates the authorized
  export addition and is not presented as final-candidate export evidence.
- Linux CI at clean `775ca5d` passed lint, 12 Rust + 285 non-database Python +
  237 PostgreSQL tests, POC and the release rehearsal. Web passed 8 unit tests,
  generated-contract drift and production build/typecheck. Packaged deployment
  passed 26 groups, including eight browser cases and four export/replay recovery
  checkpoints. The separate simulated browser case passed with zero skips/retries.
  Exact source jobs and unchanged reports are recorded in E-10–E-13.
- The retained authorized sample was also replayed locally as `0/REPRODUCED`;
  original public components and SHA-256 matched, and raw credential/key fields
  were absent. Evidence inventory, documentation links, preserved historical
  bytes and `git diff --check` were checked before publication.

README, PRD, assignment board and current handoff/security pages now acknowledge
merged PR #28 and recorded M3.1/M6 work. Full M7 remains incomplete: actual target
controls, reviewed P4 screenshots, genuine discovery notes, presentation/demo
recording and team submission evidence are still outstanding. Private-customer
retention/purge remains a separate prerequisite. This task does not deploy,
contact anyone, submit to an event or fabricate missing evidence. PR review,
current CI and merge remain required for this slice's completion.


## Item 25 — Browser CI failure diagnostics and PR #29 investigation

**Date:** October 13, 2026 (local; recorded executions below use UTC). **Owner:**
Person 3. **Branch:** `fix/browser-ci-diagnostics`, published from clean merged
PR #29 main `5ed3cc1` after fetching remote branches and checking open PRs. No
open PR or unmerged remote contribution overlapped this scope.

Implementation increment `a362619` retains an allowlisted browser result before
raising on failure or deleting temporary files. Known scenario names, expected
selection counts, attempt status/retry/duration, fixed reason/exit code and known
spec coordinates survive; raw messages, stacks, snippets, paths, stdout/stderr,
attachments, DOM and evidence do not. Malformed output, nonzero child exits,
startup/timeout, missing/duplicate/retried attempts and expected failures cannot
be reported as acceptance success. Both CI jobs upload only their exact sanitized
JSON when present, including on job failure. Deployment browser evidence is
independent of the later recovery result. Cancellation or failure before the
harness starts can still prevent report creation.

The [investigation](browser-ci.md#pr-29-intermittent-browser-failure-investigation)
records the original failed job and unchanged successful PR run/retry. Original
cause remains undetermined: the old runner discarded the failed JSON without
recording its scenario or assertion. Inspection found possible revoke/refresh
synchronization and response-loss request pacing issues for P4 triage; neither
was observed failing or attributed to PR #29. No P4 scenario, frontend source,
production limit, assertion, timeout, retry policy, auth/schema or chain policy
changed. No live RPC call was made.

### Validation

- Twenty-six focused runner checks passed, including injected secrets in errors,
  titles, counters, paths, stdout/stderr and attachments; stale-success removal;
  nonzero exit with otherwise passing JSON; and failure cleanup.
- A real Playwright assertion in a temporary standalone spec intentionally failed
  with exit 1. Its raw JSON included a private canary; the retained result kept
  the known scenario and source line 3 without the canary. The temporary private
  files were deleted. This is reporter validation, not product acceptance.
- Two clean local `a362619` packaged runs passed all eight unchanged browser
  scenarios with zero skips/retries: 2026-10-12 16:10:08–16:11:10 UTC and
  16:13:35–16:14:36 UTC, on macOS 27.0.1 arm64, Python 3.12.14, Node 26.11.0,
  Playwright 1.64.0. The first continued through all 26 deployment/recovery groups;
  the second repeated deployment/browser on fresh data. Both projects/volumes
  were removed, and Colima was restored to its originally stopped state.
- Local `make lint` passed. `make test` passed 12 Rust and 300 Python tests but
  hit the same five macOS 0.2-second process/address timeout failures recorded in
  Items 23–24; this is not a local full-suite pass. Limits remain unchanged.
- Clean Linux CI passed all four jobs at `a362619`: 12 Rust, 305 non-database
  Python, 237 PostgreSQL, lint, POC/release demo, 8 frontend unit tests, generated
  types/build, eight deployed browser cases plus all 26 recovery/deployment
  groups, and one separately simulated browser case. See
  [foundation/web/simulated](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38275414758)
  and [packaged deployment/recovery](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38275414753).
- Both browser artifact archives contained only the named sanitized JSON member;
  downloaded archive SHA-256 matched GitHub's digest. Exact reports and member
  hashes are retained in [browser-ci.md](browser-ci.md). Historical evidence and
  Items 01–24 remain byte-for-byte unchanged. Current README, PRD, assignment
  board and release bundle acknowledge merged PR #29; full M7 remains gated on
  the existing operator/P4/team handoffs.

The diagnostics/investigation slice still requires final PR review, CI and merge.
Passing repetitions do not prove the original intermittent failure is fixed.
