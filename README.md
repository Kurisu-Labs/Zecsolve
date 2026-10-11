# zecsolve

**Frontend handoff update (October 11):** [PR #12](https://github.com/Kurisu-Labs/zecsolve/pull/12) supplies the initial `apps/web` implementation. Earlier deferred labels below describe the assignment snapshot; frontend foundation and merchant previews are now implemented in part. This does not complete M6 acceptance: scoped browser roles, dashboard integration with the new case-list API, replay export, deployment integration, and full browser acceptance remain pending. Person 4 retains frontend ownership.

Resolve shielded-payment exceptions with scoped evidence and explainable merchant decisions.

The October 10 foundation runs real Glasspane output recovery against a bundled historical Zcash mainnet transaction. The valid receipt recovers **100,000 zatoshis (0.001 ZEC)**; the tampered receipt fails. Chain confirmation remains `UNAVAILABLE` because this proof of concept is offline.

Start with [TEAM_GUIDE.md](TEAM_GUIDE.md) for the codebase tour and next tasks. Original product documents are preserved in [instructions/](instructions/).

For assignments, use the [four-person feature board](docs/IMPLEMENTATION_PLAN.md#feature-board) and [task cards](docs/IMPLEMENTATION_PLAN.md#task-cards): Person 1 owns access/auth/schema, Person 2 reports/export/replay, Person 3 submission backend/live validation/release, and **Person 4 all frontend work**. Each task names its branch, prerequisites, code boundary and completion checks. The initial frontend is partially implemented in PR #12; task cards still govern remaining integration and acceptance. Listed branches do not establish completion.

Before taking a task, read [CONTRIBUTING.md](CONTRIBUTING.md): check active work, publish your task branch before implementation, push progress there, and open a PR when ready.

## Run the proof of concept

Prerequisites: an existing Rust/Cargo installation (tested with 1.99.0), Python 3.12+ (tested with 3.14.7), uv, a C compiler/linker, and make. This project uses your installed stable Rust toolchain. The first build downloads locked dependencies; subsequent fixture verification needs no network.

```sh
make setup
make poc
```

The synthetic invoice expects 200,000 zatoshis. The report shows 0 credited, 100,000 recovered as a candidate, and a projected shortfall of 100,000. It performs no database allocation and moves no funds.

Direct Rust invocation:

```sh
target/debug/zecsolve-verifier --receipt fixtures/mainnet/receipt.json --raw-tx fixtures/mainnet/transaction.hex
target/debug/zecsolve-verifier --receipt fixtures/negative/tampered-ock.json --raw-tx fixtures/mainnet/transaction.hex
```

Successful invocation exits zero even when evidence is rejected: inspect `receipt_state` and `reason_code`. Usage errors exit 64. Stdout contains one versioned JSON result; recovered memo bytes are hex, not executable or trusted display text.

## Run the API and database

```sh
cp .env.example .env
docker compose up -d db
make migrate
make api
```

Set `ZECSOLVE_POC_TOKEN` in `.env` to a randomly generated value before using the POC endpoint. Generate one with `python3 -c 'import secrets; print(secrets.token_urlsafe(32))'`. An empty token disables that endpoint. Keep `.env` private; it is ignored by Git and Docker builds.

Encrypted evidence also requires `ZECSOLVE_EVIDENCE_KEY_ID` and a base64-encoded 32-byte `ZECSOLVE_EVIDENCE_KEY`. Missing/invalid encryption configuration disables new evidence submissions and makes readiness return 503. See [key setup and evidence usage](docs/evidence.md); retain the key securely across restarts.

An existing PostgreSQL installation also works: create a dedicated database and set `ZECSOLVE_DATABASE_URL` in `.env`. Compose uses port **54329** to avoid the usual local port 5432. Credentials in Compose are for local development.

| Endpoint | Behavior |
|---|---|
| `GET /health/live` | Process is running; does not claim dependencies are ready |
| `GET /health/ready` | Checks migration revision, executable availability, and evidence encryption configuration; returns 503 when incomplete |
| `POST /api/poc/verify` | Bearer-token-protected, stateless verification of `receipt_json` and `raw_tx_hex` strings |
| `GET /api/auth/me` | Returns merchant/credential IDs derived from an active merchant credential |
| `POST /api/invoices` | Creates an immutable merchant-owned invoice and server-selected policy; requires `Idempotency-Key` |
| `GET /api/invoices/{id}` | Returns the authenticated merchant's invoice snapshot; inaccessible IDs return 404 |
| `POST /api/cases` | Opens one case per owned invoice and atomically records its opening event; requires `Idempotency-Key` |
| `GET /api/cases` | Merchant summaries with bounded cursor pagination and optional state filter; see [list contract](docs/cases.md#list-merchant-cases) |
| `GET /api/cases/{id}` | Returns current case state/version and its immutable opening event; merchant only |
| `POST /api/cases/{id}/evidence` | Stores an encrypted optional receipt/raw-tx bundle and appends an audit event; merchant + `Idempotency-Key` required |
| `GET /api/cases/{id}/evidence/{evidence_id}` | Returns owned evidence metadata only; never receipt/raw-tx content or ciphertext |
| `POST /api/cases/{id}/verify` | Verifies owned encrypted evidence and atomically stores the attempt, offline observation, evaluation, and audit event; requires `Idempotency-Key` |
| `GET /api/cases/{id}/report` | Returns merchant verification/decision history, current balances, and chain-review flags; optional `verification_id` selects a candidate |
| `POST /api/cases/{id}/resolve` | Records an authorized merchant decision with reason, reviewed case version, and retry key; production offline approvals remain blocked |
| `POST /api/cases/{id}/chain-observations` | Refreshes trusted chain evidence for a verification, including resolved cases; merchant + `Idempotency-Key` required |
| `POST /api/cases/{id}/grants`, `GET /api/cases/{id}/grants`, `DELETE /api/cases/{id}/grants/{grant_id}` | Merchant grant lifecycle; explicit case/disclosure scope, one-time secret and revocation; see [grant guide](docs/grants.md) |
| `POST /api/session`, `GET /api/session`, `DELETE /api/session` | HTTPS browser code exchange, current access scope and logout; explicit Origin configuration and CSRF required for cookie writes ([guide](docs/sessions.md)) |
| `GET /docs` | Interactive API contract; use **Authorize** to enter the POC token |

Paste the contents of `fixtures/mainnet/receipt.json` into the `receipt_json` string and `fixtures/mainnet/transaction.hex` into `raw_tx_hex`. The POC endpoint accepts content, never server file paths or fetch URLs. It does not write evidence or recovered fields to the database. The separate [persisted verification API](docs/verification.md) operates on previously submitted encrypted evidence.

To run both services in containers:

```sh
docker compose up --build
```

The backend image builds Rust in a separate stage, runs Python as an unprivileged user, and applies migrations before serving. Local ports bind only to loopback. Container runtime validation is separate from the native test suite.

## Deployment preparation

The separate [M7.1 deployment composition](docs/deployment.md) serves the built Vue app and API through TLS, with ingress limits, private API/database ports, non-root resource limits, and secret-safe runtime logs. Its production entry point disables the public POC and documentation routes. Run `python3 scripts/check_deployment.py` with Docker/Compose and OpenSSL for an isolated actual-container rehearsal.

This completes the backend preparation slice only. Browser session/cookie/Origin integration awaits M4.2; Person 4 retains frontend/browser acceptance. Live validation and full release/restore acceptance remain separate gates.

## Provision merchant identity

Merchant credentials and the identity check are implemented as part of the completed M1 backend. Apply all pending migrations with `make migrate`, then run the operator CLI from the repository root:

```sh
uv run --locked python -m zecsolve.auth.cli create-merchant --name "Demo merchant" --ttl-days 30
uv run --locked python -m zecsolve.auth.cli issue-credential --merchant-id MERCHANT_UUID --ttl-days 30
uv run --locked python -m zecsolve.auth.cli revoke-credential --credential-id CREDENTIAL_UUID
```

Creation/issuance returns one JSON object containing the merchant ID, credential ID, expiration time, and token after a successful commit. Save the token privately at that point; the database stores only its SHA-256 digest. Issuing a replacement does not revoke other credentials; explicitly revoke the old credential when rotating. Lifetimes range from 1 to 365 days, with a 30-day default.

Call `GET /api/auth/me` using `Authorization: Bearer <merchant token>`, or authorize the `MerchantCredential` scheme in `/docs`. The response contains only server-derived merchant and credential IDs. Missing, unknown, expired, or revoked credentials return 401; database unavailability returns a generic 503. This credential is separate from the existing development POC token.

Readiness now compares the database revision with the migration head discovered in `ZECSOLVE_MIGRATIONS_PATH` (default `apps/api/migrations`, relative to the launch directory). Run from the repository root or configure that path explicitly. Persisted verification, reports, and [merchant decisions](docs/resolutions.md) are available; customer/reviewer grants and browser sessions remain future increments. Credit approval remains blocked by default; see [trusted RPC configuration](docs/chain.md). Live-node validation is still pending.

## Create an invoice

Apply migration `0003` with `make migrate`, then use a merchant credential to call `POST /api/invoices` with an `Idempotency-Key`. Supply integer `expected_zat`, `network="mainnet"`, `pool="orchard"` or `"sapling"`, `receiver_address`, and optional `expected_memo`/`expires_at`. The server normalizes the receiver through Rust and stores invoice terms, policy, and retry record in one transaction.

Creation returns 201 and a `Location` header. Retrying the same credential/key/body returns the original snapshot with 200; changing the body for that key returns 409. The response contains a versioned policy and hash, not a paid status. See [the invoice API guide](docs/invoices.md) for an executable public-fixture example, exact limits, policy defaults, and migration boundaries.

After creating an invoice, use `POST /api/cases` with its `invoice_id` to open a case. Migration `0004` enforces one case per invoice and preserves historical rows. The [case API guide](docs/cases.md) explains retry behavior, audit hashes, legacy limits, and why this view is not yet a complete verification report.

## Normalize an invoice recipient

The Rust normalizer validates mainnet Orchard/Sapling recipients before invoice creation. It selects the requested receiver from a Unified Address, or decodes a standalone Sapling address, and returns the same receiver bytes used by the receipt verifier. It checks the address encoding, network, and inner receiver validity. It does not prove ownership, payment, receiver uniqueness, or chain confirmation.

Build the binary with `make build`. A request file contains only `address`, `network`, and `pool`; normalized bytes are derived by Rust, never accepted from the caller. This example uses the public historical fixture:

```sh
python3 - <<'PY'
import json
from pathlib import Path
manifest = json.loads(Path("fixtures/manifest.json").read_text())
request = {"address": manifest["expected"]["receiver_address"], "network": "mainnet", "pool": "orchard"}
Path("/tmp/zecsolve-address-request.json").write_text(json.dumps(request))
PY
target/debug/zecsolve-verifier normalize-address --input /tmp/zecsolve-address-request.json
```

Expected: `state=VALID`, `reason_code=ADDRESS_NORMALIZED`, and a `receiver` containing `network`, `pool`, and 43 bytes encoded as lowercase `receiver_hex`. The result binds the exact request file with `input_sha256`. Selecting `sapling` for this Orchard-only fixture returns `INVALID / RECEIVER_MISSING`, with no receiver.

Addresses are limited to 1,024 UTF-8 bytes, with no surrounding whitespace; the JSON request is limited to 8,192 bytes. Mainnet is the only supported requested network. Unknown fields, invalid checksums, wrong networks, missing receivers, and invalid inner receivers are rejected. Completed checks exit zero even for rejected input; bad CLI usage exits 64. Read `state` and `reason_code`, not just the exit code.

Python services can call `AddressNormalizer(settings.verifier_path, settings.verifier_timeout_seconds).normalize(NormalizeAddressRequest(address=address, network="mainnet", pool="orchard"))`, importing the adapter from `zecsolve.adapters.address` and the request model from `zecsolve.schemas.address`. The adapter uses private temporary files, a bounded subprocess, and validated JSON results. Missing executables return `UNAVAILABLE`; timeouts, crashes, oversized output, or inconsistent results return `ERROR`. Invoice creation uses this internal normalizer.

## Verify changes

```sh
make test
make lint
```

Database tests create and remove only a uniquely named test schema. Point them at a disposable database whose role can create schemas:

```sh
ZECSOLVE_TEST_DATABASE_URL='postgresql+psycopg://zecsolve:zecsolve@127.0.0.1:54329/zecsolve' make test-db
```

`make test` includes the real Rust binary, historical fixture, negative evidence, recipient normalization, rule calculations, subprocess limits, and API behavior. `make test-db` covers migrations, immutable records, merchant/invoice consistency, and concurrent output allocation. CI runs both sets. Regenerate the published API contracts with `make schema` when changing their Pydantic models.

## Current boundary

Implemented: pinned verifier integration; fixture provenance; bounded subprocess adapter; POC API; PostgreSQL models and migrations; deterministic rule contracts; operator-provisioned merchant credentials; recipient normalization; immutable invoices/policies; case opening/read and merchant case listing; encrypted merchant evidence submission and metadata; persisted real verification, offline observations and evaluation snapshots; merchant case reports and atomic resolution/allocation services; isolated simulated-confirmation demo; atomic retries and chained audit events; tests; development container configuration.

The trusted read-only Zebra adapter, idempotent refresh route, and later reorganization review are implemented. [Live endpoint validation](docs/chain.md) remains pending.

Current milestone status: **M1/M2 backend complete; M3 adapter implemented with live validation pending; M4 in progress with M4.3 locally validated; M5 pending; M6 partially implemented by Person 4; M7 release incomplete.** M4.0 shared access foundation (Person 1) remains ready. Person 3 has implemented M4.3 case listing; M4.4 customer submissions waits for M4.2 browser sessions. Person 2 can prepare packet requirements, then implement M5.0 after M4.0 merges. Follow the [assignment dependencies and definition of done](docs/IMPLEMENTATION_PLAN.md#definition-of-done); [DEVELOPMENT.md](docs/DEVELOPMENT.md) preserves historical results.

The deployed app blocks credit approval while offline; a server-configured trusted RPC source enables the policy-gated path. [The isolated M2 demo](docs/resolutions.md#isolated-first-slice-demo) proves atomic allocation using explicitly simulated confirmations; reports identify simulated decision history and no live inclusion is claimed. Assigning or merging a feature does not close the separate live-validation or full-release gates.

The current Rust wrapper accepts mainnet receipt v0 and v5 transaction branches NU5 through NU6.2. Orchard has a real historical fixture test. The Sapling recovery path uses the upstream library but does not yet have an end-to-end historical Sapling fixture in this repository. No Ironwood compatibility is claimed.

The POC token is a development access gate, not multi-merchant authorization. Only use the public fixtures until the scoped-access and private-storage milestone is complete. See [docs/security.md](docs/security.md).

## Attribution

Cryptographic recovery reuses [Glasspane](https://github.com/dolepee/glasspane) `gp-core` and `gp-types`, pinned at `f6468e6d08a7adad53bf2991a311358dc84e869b`. Its MIT license is retained in [third_party/glasspane/LICENSE](third_party/glasspane/LICENSE). Original receipt and transaction fixture bytes are recorded with hashes and source paths in [fixtures/manifest.json](fixtures/manifest.json). zecsolve contributes the adapter, workflow contracts, schema, and application foundation; it does not claim authorship of the reused cryptography.
