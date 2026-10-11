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

## Next small item

Create a merchant-owned case from an existing supported invoice snapshot, enforce one case per invoice, and write its initial audit event transactionally. Follow with encrypted evidence bundles and persisted verification/report services to finish M1.

Customer/reviewer grants, encrypted evidence, case services, approval/idempotency, trusted chain observations, frontend, and replayable exports remain pending. See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the full milestone order.
