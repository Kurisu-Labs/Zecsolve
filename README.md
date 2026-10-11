# zecsolve

Resolve shielded-payment exceptions with scoped evidence and explainable merchant decisions.

The October 10 foundation runs real Glasspane output recovery against a bundled historical Zcash mainnet transaction. The valid receipt recovers **100,000 zatoshis (0.001 ZEC)**; the tampered receipt fails. Chain confirmation remains `UNAVAILABLE` because this proof of concept is offline.

Start with [TEAM_GUIDE.md](TEAM_GUIDE.md) for the codebase tour and next tasks. Original product documents are preserved in [instructions/](instructions/).

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

An existing PostgreSQL installation also works: create a dedicated database and set `ZECSOLVE_DATABASE_URL` in `.env`. Compose uses port **54329** to avoid the usual local port 5432. Credentials in Compose are for local development.

| Endpoint | Behavior |
|---|---|
| `GET /health/live` | Process is running; does not claim dependencies are ready |
| `GET /health/ready` | Checks migration revision and executable availability; returns 503 when incomplete |
| `POST /api/poc/verify` | Bearer-token-protected, stateless verification of `receipt_json` and `raw_tx_hex` strings |
| `GET /api/auth/me` | Returns merchant/credential IDs derived from an active merchant credential |
| `POST /api/invoices` | Creates an immutable merchant-owned invoice and server-selected policy; requires `Idempotency-Key` |
| `GET /api/invoices/{id}` | Returns the authenticated merchant's invoice snapshot; inaccessible IDs return 404 |
| `GET /docs` | Interactive API contract; use **Authorize** to enter the POC token |

Paste the contents of `fixtures/mainnet/receipt.json` into the `receipt_json` string and `fixtures/mainnet/transaction.hex` into `raw_tx_hex`. The endpoint accepts content, never server file paths or fetch URLs. It does not write evidence or recovered fields to the database.

To run both services in containers:

```sh
docker compose up --build
```

The backend image builds Rust in a separate stage, runs Python as an unprivileged user, and applies migrations before serving. Local ports bind only to loopback. Container runtime validation is separate from the native test suite.

## Provision merchant identity

The first M1 increment adds merchant credentials and an identity check. Apply all pending migrations with `make migrate`, then run the operator CLI from the repository root:

```sh
uv run --locked python -m zecsolve.auth.cli create-merchant --name "Demo merchant" --ttl-days 30
uv run --locked python -m zecsolve.auth.cli issue-credential --merchant-id MERCHANT_UUID --ttl-days 30
uv run --locked python -m zecsolve.auth.cli revoke-credential --credential-id CREDENTIAL_UUID
```

Creation/issuance returns one JSON object containing the merchant ID, credential ID, expiration time, and token after a successful commit. Save the token privately at that point; the database stores only its SHA-256 digest. Issuing a replacement does not revoke other credentials; explicitly revoke the old credential when rotating. Lifetimes range from 1 to 365 days, with a 30-day default.

Call `GET /api/auth/me` using `Authorization: Bearer <merchant token>`, or authorize the `MerchantCredential` scheme in `/docs`. The response contains only server-derived merchant and credential IDs. Missing, unknown, expired, or revoked credentials return 401; database unavailability returns a generic 503. This credential is separate from the existing development POC token.

Readiness now compares the database revision with the migration head discovered in `ZECSOLVE_MIGRATIONS_PATH` (default `apps/api/migrations`, relative to the launch directory). Run from the repository root or configure that path explicitly. Merchant case endpoints, customer/reviewer grants, browser sessions, and private evidence storage remain future increments.

## Create an invoice

Apply migration `0003` with `make migrate`, then use a merchant credential to call `POST /api/invoices` with an `Idempotency-Key`. Supply integer `expected_zat`, `network="mainnet"`, `pool="orchard"` or `"sapling"`, `receiver_address`, and optional `expected_memo`/`expires_at`. The server normalizes the receiver through Rust and stores invoice terms, policy, and retry record in one transaction.

Creation returns 201 and a `Location` header. Retrying the same credential/key/body returns the original snapshot with 200; changing the body for that key returns 409. The response contains a versioned policy and hash, not a paid status. See [the invoice API guide](docs/invoices.md) for an executable public-fixture example, exact limits, policy defaults, and migration boundaries.

## Normalize an invoice recipient

The next M1 increment validates mainnet Orchard/Sapling recipients before invoice creation. It selects the requested receiver from a Unified Address, or decodes a standalone Sapling address, and returns the same receiver bytes used by the receipt verifier. It checks the address encoding, network, and inner receiver validity. It does not prove ownership, payment, receiver uniqueness, or chain confirmation.

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

Python services can call `AddressNormalizer(settings.verifier_path, settings.verifier_timeout_seconds).normalize(NormalizeAddressRequest(address=address, network="mainnet", pool="orchard"))`, importing the adapter from `zecsolve.adapters.address` and the request model from `zecsolve.schemas.address`. The adapter uses private temporary files, a bounded subprocess, and validated JSON results. Missing executables return `UNAVAILABLE`; timeouts, crashes, oversized output, or inconsistent results return `ERROR`. No public normalization or invoice endpoint is added in this increment.

## Verify changes

```sh
make test
make lint
```

Database tests create and remove only a uniquely named test schema. Point them at a disposable database whose role can create schemas:

```sh
ZECSOLVE_TEST_DATABASE_URL='postgresql+psycopg://zecsolve:zecsolve@127.0.0.1:54329/zecsolve' make test-db
```

`make test` includes the real Rust binary, historical fixture, negative evidence, recipient normalization, rule calculations, subprocess limits, and API behavior. `make test-db` covers migrations, immutable records, merchant/invoice consistency, and concurrent output allocation. CI runs both sets. Regenerate the verifier and normalization contracts with `make schema` when changing their Pydantic models.

## Current boundary

Implemented: pinned verifier integration; fixture provenance; bounded subprocess adapter; POC API; PostgreSQL models and migrations; deterministic rule contracts; operator-provisioned merchant credentials with expiry/revocation and identity endpoint; mainnet recipient normalization CLI and Python adapter; merchant invoice/policy creation and retrieval with atomic idempotent persistence; tests; development container configuration.

Next: merchant-scoped case endpoints, customer/reviewer authentication and permissions, private evidence storage, resolution services with idempotency, trusted chain observations, Vue frontend, and replayable case exports. These are not simulated behind working-looking routes.

The current Rust wrapper accepts mainnet receipt v0 and v5 transaction branches NU5 through NU6.2. Orchard has a real historical fixture test. The Sapling recovery path uses the upstream library but does not yet have an end-to-end historical Sapling fixture in this repository. No Ironwood compatibility is claimed.

The POC token is a development access gate, not multi-merchant authorization. Only use the public fixtures until the scoped-access and private-storage milestone is complete. See [docs/security.md](docs/security.md).

## Attribution

Cryptographic recovery reuses [Glasspane](https://github.com/dolepee/glasspane) `gp-core` and `gp-types`, pinned at `f6468e6d08a7adad53bf2991a311358dc84e869b`. Its MIT license is retained in [third_party/glasspane/LICENSE](third_party/glasspane/LICENSE). Original receipt and transaction fixture bytes are recorded with hashes and source paths in [fixtures/manifest.json](fixtures/manifest.json). zecsolve contributes the adapter, workflow contracts, schema, and application foundation; it does not claim authorship of the reused cryptography.
