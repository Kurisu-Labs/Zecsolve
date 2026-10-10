# zecsolve

Resolve shielded-payment exceptions with scoped evidence and explainable merchant decisions.

The October 10 foundation runs real Glasspane output recovery against a bundled historical Zcash mainnet transaction. The valid receipt recovers **100,000 zatoshis (0.001 ZEC)**; the tampered receipt fails. Chain confirmation remains `UNAVAILABLE` because this proof of concept is offline.

Start with [TEAM_GUIDE.md](TEAM_GUIDE.md) for the codebase tour and next tasks. Original product documents are preserved in [instructions/](instructions/).

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
| `GET /docs` | Interactive API contract; use **Authorize** to enter the POC token |

Paste the contents of `fixtures/mainnet/receipt.json` into the `receipt_json` string and `fixtures/mainnet/transaction.hex` into `raw_tx_hex`. The endpoint accepts content, never server file paths or fetch URLs. It does not write evidence or recovered fields to the database.

To run both services in containers:

```sh
docker compose up --build
```

The backend image builds Rust in a separate stage, runs Python as an unprivileged user, and applies migrations before serving. Local ports bind only to loopback. Container runtime validation is separate from the native test suite.

## Verify changes

```sh
make test
make lint
```

Database tests create and remove only a uniquely named test schema. Point them at a disposable database whose role can create schemas:

```sh
ZECSOLVE_TEST_DATABASE_URL='postgresql+psycopg://zecsolve:zecsolve@127.0.0.1:54329/zecsolve' make test-db
```

`make test` includes the real Rust binary, historical fixture, negative evidence, rule calculations, subprocess limits, and API behavior. `make test-db` covers migrations, immutable records, merchant/invoice consistency, and concurrent output allocation. CI runs both sets. Regenerate the verifier contract with `make schema` when changing its Pydantic model.

## Current boundary

Implemented: pinned verifier integration; fixture provenance; bounded subprocess adapter; POC API; PostgreSQL models and migration; deterministic rule contracts; tests; development container configuration.

Next: merchant/customer/reviewer authentication and permissions, case endpoints, private evidence storage, resolution services with idempotency, trusted chain observations, Vue frontend, and replayable case exports. These are not simulated behind working-looking routes.

The current Rust wrapper accepts mainnet receipt v0 and v5 transaction branches NU5 through NU6.2. Orchard has a real historical fixture test. The Sapling recovery path uses the upstream library but does not yet have an end-to-end historical Sapling fixture in this repository. No Ironwood compatibility is claimed.

The POC token is a development access gate, not multi-merchant authorization. Only use the public fixtures until the scoped-access and private-storage milestone is complete. See [docs/security.md](docs/security.md).

## Attribution

Cryptographic recovery reuses [Glasspane](https://github.com/dolepee/glasspane) `gp-core` and `gp-types`, pinned at `f6468e6d08a7adad53bf2991a311358dc84e869b`. Its MIT license is retained in [third_party/glasspane/LICENSE](third_party/glasspane/LICENSE). Original receipt and transaction fixture bytes are recorded with hashes and source paths in [fixtures/manifest.json](fixtures/manifest.json). zecsolve contributes the adapter, workflow contracts, schema, and application foundation; it does not claim authorship of the reused cryptography.
