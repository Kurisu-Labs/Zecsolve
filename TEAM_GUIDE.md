# zecsolve teammate guide

**Frontend handoff update (October 11):** [PR #12](https://github.com/Kurisu-Labs/zecsolve/pull/12) supplies the initial `apps/web` implementation. Earlier deferred labels below describe the assignment snapshot; frontend foundation and merchant previews are now implemented in part. This does not complete M6 acceptance: scoped browser roles, dashboard integration with the new case-list API, replay export, deployment integration, and full browser acceptance remain pending. Person 4 retains frontend ownership.

This guide explains the foundation and backend milestones completed through October 12. Use [README.md](README.md) for runnable setup commands.

## What we are building

zecsolve helps merchants investigate shielded Zcash payments that do not match an invoice. A customer supplies an output-specific receipt; the verifier recovers the selected amount, receiver, and memo; deterministic rules explain the match; the merchant decides whether to allocate credit. The versioned case packet preserves authorized evidence and decisions for offline replay.

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
| API | Health/readiness, POC verification, owned invoice/case create/read, paginated merchant case listing, encrypted evidence upload/metadata, persisted verification, reports, merchant decisions, customer claims, scoped reviewer reads and authorized export | P4 actual-browser integration |
| Database | Immutable snapshots, one case per invoice, encrypted evidence, verification/evaluation history, chained events, atomic decisions/allocations/retries | Retention/rotation workflows |
| Rules | Aggregate approved balances, candidate projection, mismatch/conflict findings, persisted invoice policy | Real-node integration validation; the trusted RPC adapter is implemented and offline remains the default |
| Access | Merchant credentials, customer/reviewer grants, consent selection, HTTPS browser sessions and authorization rechecks | P4 browser disclosure/acceptance |
| Frontend | Initial Vue implementation in PR #12; Person 4 owns it | Remaining actual-backend and browser integration |
| Export | CasePacketV1, authorized snapshot export and offline historical replay | P3 export/replay recovery integration, P4 download flow and final release rehearsal |

The POC runs without PostgreSQL; readiness requires a migrated database, verifier executable, and configured evidence encryption key. Database tests use public fixtures or synthetic rows. They prove the implemented workflow/database behavior; simulated RPC responses do not establish live chain inclusion.

## Code map

| Path | Responsibility |
|---|---|
| `crates/zecsolve-verifier/src/main.rs` | Offline Rust executable; delegates recovery to Glasspane and emits bounded JSON |
| `Cargo.toml`, `Cargo.lock` | Pinned Glasspane revision and resolved Rust dependencies |
| `pyproject.toml`, `uv.lock` | Single Python package, development tools, and locked dependencies |
| `apps/api/src/zecsolve/main.py` | FastAPI assembly, POC authentication, health endpoints, request limit and concurrency bound |
| `apps/api/src/zecsolve/config.py` | Typed environment settings; secret values use `SecretStr` |
| `apps/api/src/zecsolve/auth/` | Merchant credential issuance/revocation CLI and server-derived authentication dependency |
| `apps/api/src/zecsolve/api/invoices.py`, `services/invoices.py` | Merchant-owned invoice routes, atomic snapshot creation, and idempotent retries |
| `apps/api/src/zecsolve/api/cases.py`, `services/cases.py` | Case creation/read, initial event persistence, and semantic/idempotent replay |
| `apps/api/src/zecsolve/services/workflow.py`, `api/workflow.py` | Shared transaction, post-lock credential checks, key validation, and safe HTTP errors |
| `apps/api/src/zecsolve/domain/events.py` | Versioned opening event and separate payload/header hashes |
| `apps/api/src/zecsolve/adapters/evidence_crypto.py` | AES-256-GCM, scoped associated data, key availability, and integrity checks |
| `apps/api/src/zecsolve/api/evidence.py`, `services/evidence.py` | Merchant bundle submission, metadata reads, internal authorized decryption, and atomic retries |
| `apps/api/src/zecsolve/api/verifications.py`, `services/verifications.py` | Authorized decryption, real verifier execution, atomic attempt/evaluation/event persistence and retry |
| `apps/api/src/zecsolve/services/reports.py`, `services/verification_records.py` | Consistent owned report snapshots and validation of stored attempts |
| `apps/api/src/zecsolve/domain/offline_evaluation.py`, `schemas/workflow_verification.py` | Captured evaluation inputs, offline balances, and initial report contracts |
| `apps/api/src/zecsolve/api/resolutions.py`, `services/resolutions.py`, `services/resolution_records.py` | Merchant actions, atomic allocation, retry, version checks, and persisted decision validation |
| `apps/api/src/zecsolve/domain/decision_rules.py`, `services/observations.py` | Versioned policy gates and immutable refresh diagnostics; default observer has no trusted confirmation source |
| `apps/api/src/zecsolve/adapters/rpc.py`, `api/observations.py`, `services/chain_review.py` | Trusted read-only RPC, idempotent merchant refresh, and later loss-of-inclusion review |
| `scripts/demo_resolution.py` | Same-service allocation demo in a temporary schema with clearly simulated confirmation |
| `apps/api/src/zecsolve/services/audit.py` | Validates the stored event chain before extending it |
| `apps/api/src/zecsolve/domain/snapshots.py` | Versioned deterministic serialization and invoice snapshot hashes |
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
- **No double credit:** Same output and same invoice is an idempotent retry. Same output and another invoice is a conflict. The resolution service catches the database uniqueness race and reauthorizes the winning outcome.
- **Approved versus candidate:** `credited_zat` sums unique approved allocations. `candidate_zat` is an unallocated, matching recovered output. A projected balance is not paid status.
- **Separate facts:** Receipt validity, chain observation, case state, and business resolution are independent. The current offline POC can never claim confirmed chain inclusion.
- **Separate failures:** Missing receipt → `NONE`; absent source/binary → `UNAVAILABLE`; unimplemented format → `UNSUPPORTED`; failed binding/recovery → `INVALID`; process or malformed transaction data errors → `ERROR`.
- **Multiple findings:** Chain uncertainty and a balance shortfall may coexist. Invalid evidence is not a fraud accusation.
- **Recipient comparison:** Domain rules consume normalized receiver bytes plus pool/network. Invoice creation decodes Unified Addresses before comparing receivers. A receipt label is not a verified memo.
- **Invoice binding:** Require an exact expected memo match or an explicitly established unique receiver binding. Otherwise return `NEEDS_REVIEW`. A matching amount alone does not identify an invoice; a projected overpayment also requires review.
- **Merchant authority:** Verification and rule evaluation never write allocations. The merchant resolution service rechecks stale state and commits approval, allocation, and audit event together; deployed offline observations block credit.

The [persisted workflow](docs/verification.md) decrypts an owned bundle, runs Rust outside database locks, and records an immutable attempt, offline observation, evaluation, and event together. Reports use one consistent database snapshot and project only the latest or explicitly selected candidate; they never sum unapproved attempts. Recovered memo/receiver fields are merchant disclosures and remain outside application encryption.

The POC constructs a synthetic 200,000-zatoshi invoice over the historical 100,000-zatoshi output. With offline observations it shows **0 credited** and **100,000 projected shortfall**. The isolated simulated-confirmation demo separately exercises merchant approval and credited balances. This distinction is intentional.

## Database conventions

`invoices` store immutable snapshots from creation. Corrections require a new snapshot; the next service milestone must define version linkage. Cases inherit merchant ownership through a composite foreign key. This constraint is not a replacement for authorization on every query.

`output_allocations` use the full output identity as their primary key and contain only approved allocations. Pending candidates belong in verification/rule results. Allocations reference both a verification and a resolution. Database tests confirm only one concurrent insert can win.

Invoice/policy snapshots, retry records, evidence metadata/content, verification attempts, resolutions, output allocations, and case events reject updates/deletes. A database administrator can still alter these controls; do not describe the history as immutable against an operator or independently notarized. Opening, evidence-submission, verification, and decision events have transactional writers and verifiable payload/header hashes. Offline observations and evaluation snapshots also reject ordinary edits/deletes. Evidence retention and key rotation need a separate design that preserves nonce reservations.

Use Alembic for future changes. Do not call `Base.metadata.create_all()` at application startup. Once teammates have applied a migration, add a new one rather than rewriting it.

## Assigned next work streams

| Owner / work stream | First deliverable | Integration boundary |
|---|---|---|
| Person 1 — access | M4.0–M4.2 access foundation, grants and sessions merged | Own shared auth/models/migrations; consumers reuse the same authorization context |
| Person 2 — reports/export | M4.5/M5 backend implemented; see task board for PR integration | Own disclosure projections, packet contract, replay and export; private merchant storage already exists |
| Person 3 — workflow/integration/release | Listing, submissions, deployment/recovery preparation merged; live validation needs an endpoint | Own submission services and deployment; consume access contracts and Person 4's built app |
| Person 4 — all frontend | M6.0 Vue shell when frontend work is resumed | Own UI/client/types/styles/accessibility/build and browser tests; actual-backend integration required for completion |

These are the user's four numbered assignment slots; record the actual contributor when claiming a task. The [assignment board and task cards](docs/IMPLEMENTATION_PLAN.md#3-ownership-and-feature-tasks) define branch names, prerequisites, ownership, exclusions, interfaces and acceptance checks. All M6 work remains deferred despite Person 4's assignment. No teammates have been messaged. Agree and merge prerequisite contracts before dependent implementation; serialize shared integration files. Keep CipherPay, notifications, browser WASM, signatures and live checkout outside this P0 path. A historical Sapling fixture is a separate future coverage item, not a substitute for M3.1 live validation.

## Before handing off a change

Follow [CONTRIBUTING.md](CONTRIBUTING.md) from the start of each task: inspect active branches/PRs, publish a clearly named task branch before implementation, and push progress on that branch. Open a PR when the task is complete; review and merge it into `main`, then delete the merged branch. Coordinate overlapping scope before editing shared code.

Run `make test` and `make lint`. Run `make test-db` with a disposable PostgreSQL URL for model, migration, or allocation changes. Regenerate the schema with `make schema` after changing the verification contract. Check that exports/logs/errors do not expose tokens, wallet keys or unnecessary receipt content.

Commit source and lockfiles, not `.env`, `.venv`, `.cache`, `target`, or real customer evidence. Fixtures in this repository are already-public upstream demo artifacts. The original specification files should remain reference inputs; document implementation changes here or in architecture notes.

## Trusted chain handoff (M3)

Read [docs/chain.md](docs/chain.md) before configuring a node. The adapter is composed only from server settings; request bodies cannot supply URLs or trust assertions. New approvals always refresh; a merchant can also refresh an already resolved case with `POST /api/cases/{id}/chain-observations`. Keep the existing observation-v1 snapshot format intact: observation-v2 adds sanitized RPC provenance without changing older decision hashes.

The user has no RPC endpoint yet. The live historical-fixture observation and merchant-approval trace are **pending**, as is recording the actual node version/capabilities. The initial frontend is recorded in PR #12. M4/M5 backend now supplies merchant listing, grants, sessions, claims, scoped reports and replay packets. Browser acceptance and full release validation remain separate gates.

## P2 report/export/replay handoff

- `schemas/disclosure.py` and `services/reviewer_reports.py` define explicit
  consented reviewer fields. Case detail/listing remain merchant-only.
- `schemas/packet.py` and `domain/packets.py` define original byte encodings,
  historical hash bases, complete/limited scope and integrity.
- `replay/` implements `replay-case` with fixed local historical dispatch and
  separate integrity/recovery/arithmetic/external-context results.
- `services/exports.py` captures one authorized database snapshot, decrypts
  outside the transaction and reauthorizes before disclosure.

Start with [scoped report fields](docs/scoped-reports.md) and [packet/export/replay
usage](docs/packets.md). Public/synthetic fixtures and recorded CLI outcomes are
in `fixtures/packets/`. Do not use packet-provided strings as HTML, executable
paths or URLs to fetch. Live validation is still pending; no frontend work was
included in this P2 implementation.
