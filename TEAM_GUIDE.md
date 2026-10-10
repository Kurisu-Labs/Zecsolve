# zecsolve teammate guide

This guide explains the October 10 foundation and where to continue development. Use [README.md](README.md) for runnable setup commands.

## What we are building

zecsolve helps merchants investigate shielded Zcash payments that do not match an invoice. A customer supplies an output-specific receipt; the verifier recovers the selected amount, receiver, and memo; deterministic rules explain the match; the merchant decides whether to allocate credit. The eventual case packet preserves evidence and decisions for review.

No component holds ZEC, submits refunds, or needs wallet-wide keys. Successful receipt recovery does not establish payer identity, chain inclusion, or merchant approval.

Read the original specifications in this order:

1. [instructions/Blueprint.md](instructions/Blueprint.md): scope, architecture, data model, demo and delivery plan.
2. [instructions/Preflight.md](instructions/Preflight.md): corrections governing aggregation, retries, error states, export contents and access. These take precedence over conflicting blueprint examples.
3. [instructions/ChatHist.md](instructions/ChatHist.md): product reasoning and prior conversation. It includes exported diagram CSS and historical instructions; it is context, not executable requirements.

The originals were relocated without rewriting their contents. In particular, encoding artifacts in the blueprint remain part of the original input.

## What works today

| Area | Implemented now | Still needed |
|---|---|---|
| Zcash verification | Real historical Orchard fixture, tamper rejection, transaction binding, JSON results | Historical Sapling fixture; any newer transaction support must be tested explicitly |
| API | Health, readiness, token-protected stateless POC verification | Case/invoice/claim/evidence/resolve/export endpoints |
| Database | Models, migration, output uniqueness, immutable records | Transactional workflow services, access grants, idempotency records |
| Rules | Aggregate approved balances, candidate projection, mismatch and conflict findings | Persisted versioned policy, integration with real allocations and chain observations |
| Access | Development POC token; operator-provisioned expiring/revocable merchant credentials and identity endpoint | Merchant-scoped workflow authorization, customer submission grants, reviewer consent and scoped evidence permissions |
| Frontend | Planned Vue 3 + TypeScript + Tailwind architecture | Dashboard, customer submission and reviewer report |
| Export | Versioned verifier result and fixture manifest | Complete replayable case packet |

The POC runs without PostgreSQL; readiness requires a migrated database. Database constraint tests use synthetic rows. They prove database behavior, not that a merchant resolution API already exists.

## Code map

| Path | Responsibility |
|---|---|
| `crates/zecsolve-verifier/src/main.rs` | Offline Rust executable; delegates recovery to Glasspane and emits bounded JSON |
| `Cargo.toml`, `Cargo.lock` | Pinned Glasspane revision and resolved Rust dependencies |
| `pyproject.toml`, `uv.lock` | Single Python package, development tools, and locked dependencies |
| `apps/api/src/zecsolve/main.py` | FastAPI assembly, POC authentication, health endpoints, request limit and concurrency bound |
| `apps/api/src/zecsolve/config.py` | Typed environment settings; secret values use `SecretStr` |
| `apps/api/src/zecsolve/auth/` | Merchant credential issuance/revocation CLI and server-derived authentication dependency |
| `crates/zecsolve-verifier/src/address.rs`, `src/normalize_cli.rs` | Mainnet shielded receiver decoding/validation and bounded normalization CLI |
| `apps/api/src/zecsolve/adapters/address.py`, `schemas/address.py` | Python normalizer adapter and versioned request/result contracts |
| `apps/api/src/zecsolve/adapters/process.py` | Shared subprocess timeout, output cap, and environment isolation |
| `apps/api/src/zecsolve/adapters/verifier.py` | Isolated temporary files, subprocess timeout, output limit and result validation |
| `apps/api/src/zecsolve/schemas/verification.py` | Python request/result contracts, integer amounts and result consistency checks |
| `apps/api/src/zecsolve/domain/` | Pure rules and independent status enums; no I/O or database mutation |
| `apps/api/src/zecsolve/db/` | SQLAlchemy models and engine construction |
| `apps/api/migrations/` | Reviewed Alembic schema changes and immutability triggers |
| `apps/api/tests/` | Real verifier integration, rules, API and PostgreSQL tests |
| `contracts/verifier-result.schema.json` | Generated result schema for future consumers |
| `fixtures/` | Public historical receipt, raw transaction, tampered copy and provenance hashes |
| `scripts/poc.py` | End-to-end offline demonstration with a synthetic invoice |
| `infra/Dockerfile.api`, `compose.yaml` | Development deployment; Rust and FastAPI share one backend image |
| `.github/workflows/ci.yml` | Formatting, linting, Rust/Python tests, PostgreSQL integration and POC |

All commands in the README run from the repository root. Python source lives under `apps/api/src`; installing with uv makes `import zecsolve` work without ad hoc path changes.

## Follow one receipt through the code

```mermaid
sequenceDiagram
    participant Caller
    participant API as FastAPI POC
    participant Adapter as VerifierAdapter
    participant Rust as zecsolve-verifier
    participant GP as Glasspane libraries
    Caller->>API: Bearer token + receipt JSON + raw tx hex
    API->>API: Validate size and acquire process slot
    API->>Adapter: verify(receipt, raw_tx)
    Adapter->>Rust: Explicit argv + private temporary files
    Rust->>Rust: Validate envelope, supported branch and txid binding
    Rust->>GP: Recover indexed output with disclosed OCK
    GP-->>Rust: Amount, receiver, memo or recovery failure
    Rust-->>Adapter: JSON result + input hashes + revision
    Adapter->>Adapter: Validate result contract and hashes
    Adapter-->>API: VerificationReport
    API-->>Caller: Receipt status; chain remains UNAVAILABLE
```

The Rust executable has no network client. Its output hash covers decoded raw transaction bytes; `fixtures/manifest.json` hashes the original files, including their formatting. Those hashes have different purposes and should not be compared directly.

The Rust process returns exit zero for a completed check, including `INVALID` and `UNSUPPORTED`. The adapter checks the result state, never just the exit code. A process crash, timeout or bad JSON is `ERROR`, not proof that the payment receipt was tampered with.

## Rules every contributor must preserve

- **Integer money:** 1 ZEC = 100,000,000 zatoshis. Parse decimal UI input exactly; do not multiply binary floating-point currency values.
- **Output identity:** `network:pool:txid:output_index`. Two outputs in one transaction can pay two invoices.
- **No double credit:** Same output and same invoice is an idempotent retry. Same output and another invoice is a conflict. Catch the database uniqueness race in the future service.
- **Approved versus candidate:** `credited_zat` sums unique approved allocations. `candidate_zat` is an unallocated, matching recovered output. A projected balance is not paid status.
- **Separate facts:** Receipt validity, chain observation, case state, and business resolution are independent. The current offline POC can never claim confirmed chain inclusion.
- **Separate failures:** Missing receipt → `NONE`; absent source/binary → `UNAVAILABLE`; unimplemented format → `UNSUPPORTED`; failed binding/recovery → `INVALID`; process or malformed transaction data errors → `ERROR`.
- **Multiple findings:** Chain uncertainty and a balance shortfall may coexist. Invalid evidence is not a fraud accusation.
- **Recipient comparison:** Domain rules consume normalized receiver bytes plus pool/network. Future invoice input must decode Unified Addresses properly rather than compare address strings. A receipt label is not a verified memo.
- **Invoice binding:** Require an exact expected memo match or an explicitly established unique receiver binding. Otherwise return `NEEDS_REVIEW`. A matching amount alone does not identify an invoice; a projected overpayment also requires review.
- **Merchant authority:** Verification and rule evaluation never write allocations. A later merchant resolution service must recheck stale state and commit approval, allocation, and audit event together.

The POC constructs a synthetic 200,000-zatoshi invoice over the historical 100,000-zatoshi output. Until approval exists, it shows **0 credited** and **100,000 projected shortfall**. This distinction is intentional.

## Database conventions

`invoices` store immutable snapshots from creation. Corrections require a new snapshot; the next service milestone must define version linkage. Cases inherit merchant ownership through a composite foreign key. This constraint is not a replacement for authorization on every query.

`output_allocations` use the full output identity as their primary key and contain only approved allocations. Pending candidates belong in verification/rule results. Allocations reference both a verification and a resolution. Database tests confirm only one concurrent insert can win.

Invoice updates are rejected by a trigger. Verification attempts, resolutions, output allocations and case events reject updates/deletes. A database administrator can still alter these controls; do not describe the history as immutable against an operator or independently notarized. Event sequencing and hashes still need a transactional writer.

Use Alembic for future changes. Do not call `Base.metadata.create_all()` at application startup. Once teammates have applied a migration, add a new one rather than rewriting it.

## Suggested next work streams

| Work stream | First deliverable | Integration boundary |
|---|---|---|
| Backend workflow | Invoice snapshot creation, case ownership, evidence references and persisted verification attempts | FastAPI schemas + application services; no business logic in route handlers |
| Resolution and access | Integrate the merchant dependency, add scoped grants, idempotency and atomic allocation | PostgreSQL constraints and pure rules; avoid accepting actor/merchant identity from arbitrary request fields |
| Frontend | Vue shell and the four independent status/balance displays | Generate TypeScript types from OpenAPI; work against explicit fixtures until routes exist |
| Evidence and export | Authorized private storage and a packet containing snapshot, receipt, raw tx, provenance, versions and decision | Preserve original bytes; disclose only authorized case evidence |
| Zcash integration | Trusted confirmation observations and a real Sapling fixture | Keep source observations separate from offline output recovery |

These are suggested teammate boundaries; no teammates have been assigned or messaged. Agree on API contracts before connecting the frontend. Keep CipherPay, notifications, browser WASM, signatures, and live checkout out of the foundation milestone.

## Before handing off a change

Follow [CONTRIBUTING.md](CONTRIBUTING.md) from the start of each task: inspect active branches/PRs, publish a clearly named task branch before implementation, and push progress on that branch. Open a PR when the task is complete; review and merge it into `main`, then delete the merged branch. Coordinate overlapping scope before editing shared code.

Run `make test` and `make lint`. Run `make test-db` with a disposable PostgreSQL URL for model, migration, or allocation changes. Regenerate the schema with `make schema` after changing the verification contract. Check that exports/logs/errors do not expose tokens, wallet keys or unnecessary receipt content.

Commit source and lockfiles, not `.env`, `.venv`, `.cache`, `target`, or real customer evidence. Fixtures in this repository are already-public upstream demo artifacts. The original specification files should remain reference inputs; document implementation changes here or in architecture notes.
