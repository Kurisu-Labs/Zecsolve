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
