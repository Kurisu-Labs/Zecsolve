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

## Next small item

Normalize a supplied recipient address using the pinned Rust `zcash_address` dependency, checking network and requested shielded pool. Add a separate bounded CLI mode/adapter and targeted address tests before allowing clients to create invoices. After that, add the authenticated immutable invoice/policy creation service and endpoint.

Customer/reviewer grants, encrypted evidence, case services, approval/idempotency, trusted chain observations, frontend, and replayable exports remain pending. See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the full milestone order.
