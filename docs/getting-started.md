# Getting started

This guide covers local verification, API development, browser access, and offline replay. All commands run from the repository root unless noted. For a product overview and a public browser demo, see [the README](../README.md).

## Prerequisites and setup

Use Rust/Cargo 1.99+, Python 3.12+, uv, a C compiler/linker, and make. The native backend targets POSIX environments; use Linux or macOS, or the Docker composition for a containerized runtime. Frontend development also requires Node.js 24+. PostgreSQL 17 is the version used by Compose and CI.

```sh
make setup
make poc
```

Setup installs locked Python dependencies and builds the Rust verifier. The POC uses the public historical fixture and a synthetic 200,000-zatoshi invoice, with no database or live RPC. It recovers a 100,000-zatoshi candidate, credits zero, and reports a projected 100,000-zatoshi shortfall. The tampered receipt is rejected.

## Run the verifier directly

```sh
target/debug/zecsolve-verifier --receipt fixtures/mainnet/receipt.json --raw-tx fixtures/mainnet/transaction.hex
target/debug/zecsolve-verifier --receipt fixtures/negative/tampered-ock.json --raw-tx fixtures/mainnet/transaction.hex
```

A completed check exits zero even when evidence is rejected; inspect `receipt_state` and `reason_code`. Usage errors exit 64. Stdout contains one versioned JSON result. Recovered memo bytes are hex, not executable or trusted display text. Offline recovery does not establish chain confirmation.

## Run the API and database

After `make setup`, create your local configuration if you do not already have one:

```sh
cp .env.example .env
```

Before starting the API, configure these values privately in `.env`:

| Setting | Purpose |
|---|---|
| `ZECSOLVE_DATABASE_URL` | The example targets the local Compose database on port 54329. An existing dedicated PostgreSQL database also works. |
| `ZECSOLVE_EVIDENCE_KEY_ID` | A stable, nonsecret identifier for the encryption key, such as `local-v1`. |
| `ZECSOLVE_EVIDENCE_KEY` | Base64 of 32 random bytes; see [key setup](evidence.md#configure-the-encryption-key). Keep the same key and ID across restarts. |
| `ZECSOLVE_POC_TOKEN` | Optional random bearer token for the development POC endpoint. An empty value disables that endpoint. This is separate from merchant credentials. |

Missing or invalid evidence encryption configuration makes readiness return 503 and disables new evidence submissions. Keep `.env` and keys private; retain an independent secure copy of the evidence key before storing data you need to recover.

```sh
docker compose up -d db --wait
make migrate
make api
```

The native API listens at `http://127.0.0.1:8000`. The development-only database credentials in Compose are not suitable for a public deployment. `make migrate` applies all pending migrations; readiness checks the current migration head, executable availability, and evidence encryption configuration.

To run the database and API in containers instead, configure `.env` as above, then use:

```sh
docker compose up --build
```

The development image builds Rust, runs the API as an unprivileged user, and applies migrations before serving. Local ports bind only to loopback. This composition is for API development; authenticated browser access requires the HTTPS setup below.

### Development API reference

Open `http://127.0.0.1:8000/docs` for the interactive contract. Use the POC bearer token for `POST /api/poc/verify`, or the `MerchantCredential` scheme for merchant routes. Public deployment entry points disable `/docs`, `/openapi.json`, and the POC route.

For stateless POC verification, pass the contents of `fixtures/mainnet/receipt.json` and `fixtures/mainnet/transaction.hex` as the `receipt_json` and `raw_tx_hex` strings. This endpoint accepts contents, not server paths or URLs, and does not persist evidence or recovered fields.

| API area | Entry points | Guide |
|---|---|---|
| Health | `GET /health/live`, `GET /health/ready` | Liveness is process status; readiness checks dependencies, not chain confirmation. |
| Merchant identity | `GET /api/auth/me` | [Access](access.md) |
| Invoices | `POST /api/invoices`, `GET /api/invoices/{id}` | [Invoice creation and recipient binding](invoices.md) |
| Cases | `POST /api/cases`, `GET /api/cases`, `GET /api/cases/{id}` | [Case creation, reads, and pagination](cases.md) |
| Claims and evidence | `POST /api/cases/{id}/claims`, `POST /api/cases/{id}/evidence` | [Consent and customer submissions](customer-submissions.md) |
| Verification | `POST /api/cases/{id}/verify` | [Persisted verification](verification.md) |
| Chain and decisions | `POST /api/cases/{id}/chain-observations`, `POST /api/cases/{id}/resolve` | [Trusted RPC](chain.md), [merchant decisions](resolutions.md) |
| Reports and evidence reads | `GET /api/cases/{id}/report`, `GET /api/cases/{id}/evidence/{evidence_id}`, `GET /api/cases/{id}/evidence/{evidence_id}/content` | [Authorized disclosures](scoped-reports.md) |
| Export | `GET /api/cases/{id}/export` | [Packets and offline replay](packets.md) |
| Case grants | `POST`/`GET /api/cases/{id}/grants`, `DELETE /api/cases/{id}/grants/{grant_id}` | [Grant lifecycle](grants.md) |
| Browser sessions | `POST`/`GET`/`DELETE /api/session` | [HTTPS sessions and CSRF](sessions.md) |

Workflow writes use `Idempotency-Key`; retain the same key when retrying an unchanged request. The individual guides describe authorization, request limits, and retry/conflict behavior.

## Provision merchant identity

With migrations applied and your private database configuration loaded, run the operator CLI:

```sh
uv run --locked python -m zecsolve.auth.cli create-merchant --name "Demo merchant" --ttl-days 30
```

Creation returns merchant/credential IDs, expiration, and the token once after a successful commit. Save the token privately; the database stores only its SHA-256 digest. Credentials last 1–365 days, with a 30-day default. For later issuance or revocation, substitute the returned IDs:

```sh
uv run --locked python -m zecsolve.auth.cli issue-credential --merchant-id MERCHANT_UUID --ttl-days 30
uv run --locked python -m zecsolve.auth.cli revoke-credential --credential-id CREDENTIAL_UUID
```

Issuing a replacement does not revoke the old credential. API clients use `Authorization: Bearer <merchant token>`; browser users enter the code at `/connect` on the configured HTTPS origin. Missing, expired, or revoked credentials return 401. See [access](access.md), [grants](grants.md), and [sessions](sessions.md) for the role boundaries.

## Create an invoice and case

Use a merchant credential and `Idempotency-Key` with `POST /api/invoices`. Supply integer `expected_zat`, `network="mainnet"`, `pool="orchard"` or `"sapling"`, `receiver_address`, and optional `expected_memo`/`expires_at`. The server normalizes the receiver and stores immutable invoice terms and its selected policy together.

Creation returns 201; an identical retry returns the original snapshot with 200, while a changed body under the same key returns 409. This creates invoice terms, not a paid status. Follow the [executable invoice example](invoices.md), then use `POST /api/cases` with `invoice_id` to open the case. [Case rules](cases.md) enforce one case per invoice.

## Normalize an invoice recipient

The normalizer decodes mainnet Orchard/Sapling recipients, including the selected receiver in a Unified Address, into the bytes used by receipt recovery. It validates encoding, network, and receiver validity, not address ownership or payment.

After `make setup`, create a request from the public fixture:

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

Expect `state=VALID`, `reason_code=ADDRESS_NORMALIZED`, the normalized receiver, and an `input_sha256` binding the request file. Selecting Sapling for this Orchard-only fixture yields `INVALID / RECEIVER_MISSING`. As with verification, inspect the state rather than relying on exit zero. The versioned [request](../contracts/normalize-address-request.schema.json) and [result](../contracts/normalize-address-result.schema.json) schemas define the interface; invoice creation calls the internal Python adapter automatically.

## Run the frontend

For browser demo development, install Node.js 24+ and run:

```sh
cd apps/web
npm ci
npm run dev
```

Vite serves the app at `http://localhost:5173` and proxies `/api` to `127.0.0.1:8000`. Demo mode works over HTTP and uses recorded fixture outcomes. Real browser sessions require HTTPS and an exact `ZECSOLVE_BROWSER_ORIGINS` value; there is no insecure-cookie bypass. Follow [Docker deployment](deployment.md) for the app/API on one HTTPS origin, or the [frontend browser harness](../apps/web/README.md#actual-backend-browser-acceptance) for isolated integration testing.

See [the frontend guide](../apps/web/README.md) for build commands, generated contract types, routes, and browser tests. The [Vercel guide](vercel-deployment.md) covers the existing hosted demo and its manual release procedure.

## Replay an authorized packet offline

After `make setup`:

```sh
uv run --locked replay-case fixtures/packets/complete-v1.json
uv run --locked replay-case /path/to/authorized-packet.json
```

Replay checks integrity, real receipt recovery, and historical rules/arithmetic without opening a database or changing credit. Scoped omissions or missing/unsupported versions cannot claim complete replay. Fixture approvals are explicitly simulated; replay cannot freshly prove chain inclusion or authenticate business assertions. See [packet usage and exit codes](packets.md#offline-replay-m51).

## Verify changes

```sh
make test
make lint
```

Database tests create and remove only a uniquely named test schema. Point them at a disposable database whose role can create schemas:

```sh
ZECSOLVE_TEST_DATABASE_URL='postgresql+psycopg://zecsolve:zecsolve@127.0.0.1:54329/zecsolve' make test-db
```

`make test` covers the real Rust verifier, public and negative fixtures, normalization, rules, adapter limits, and API behavior. `make test-db` covers migrations, immutable records, ownership, and concurrent allocation. Follow [CONTRIBUTING.md](../CONTRIBUTING.md) for the required checks for each change.
