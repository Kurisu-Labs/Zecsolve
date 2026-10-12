# Zecsolve — P0 Implementation and Assignment Board

**Person 4 frontend integration (October 12):** The user resumed frontend work and authorized local implementation while GitHub authentication was unavailable. M6 integration and actual-backend browser evidence are available on `feat/m6-frontend-integration`; see [frontend handoff](frontend.md). PR #26 is published; review, CI and merge remain pending.

**Historical frontend handoff (October 11):** [PR #12](https://github.com/Kurisu-Labs/zecsolve/pull/12) supplied the initial app. The October 12 local integration in [frontend.md](frontend.md) supersedes that partial implementation status; review/CI/merge still govern completion.

**Baseline:** October 10, 2026

**Assignment/status update:** October 12, 2026

**Requirements:** [PRD](PRD.md), especially §§6–7 and acceptance scenarios A-01 through A-15

**Status:** M1/M2 backend implementation is complete. M3 adapter/refresh has a [recorded live-node/approval pass](chain.md#recorded-live-run); its evidence merged in PR #27. M4.0–M4.5 are merged. M5.0–M5.2 merged in PRs #21–#23. Person 4's frontend integration is implemented and browser-validated locally; PR #26 is published; review/CI/merge remain pending (see [frontend.md](frontend.md)). M7.1 backend preparation is merged in PR #17. Person 3's M7.2 backend recovery and scoped export/replay integration are merged in PRs #19/#24; full M7 release remains incomplete. The [release evidence index](release-evidence.md) maps acceptance rows to recorded runs and remaining owners. Recorded implementation results remain in [DEVELOPMENT.md](DEVELOPMENT.md).

**Start here:** [ownership and feature tasks](#3-ownership-and-feature-tasks), [task cards](#task-cards), and [definition of done](#definition-of-done). Milestone requirements below remain the acceptance specification; the board is the current assignment and dependency source of truth.

**First milestone:** Invoice → receipt verification → merchant-approved allocation → report

**Confirmed sequencing:** Start with the public historical fixture and explicitly simulated test confirmations; add trusted live confirmation before release

## 1. First deliverable and boundaries

Build one backend workflow through the real Rust verifier, real PostgreSQL transactions, and a versioned JSON case report before building the full frontend. An integration test and a local demo script must exercise the same application services that the HTTP routes call.

### First-slice acceptance

1. Provision a merchant credential and create an immutable mainnet Orchard invoice for **200,000 zatoshis**, using the receiver and memo from the existing public fixture.
2. Open a case, upload the existing receipt and raw transaction, and persist the real verifier result. Do not synthesize recovered fields.
3. With the offline observer, report `VALID` receipt evidence, `UNAVAILABLE` chain observation, **0 credited**, **200,000 outstanding**, **100,000 candidate**, and **100,000 projected outstanding**. Approval must be blocked.
4. In the isolated test/demo harness only, inject a clearly labeled simulated confirmed observation bound to the verified transaction. The merchant explicitly approves the recovered output through the normal resolution service.
5. Commit exactly one allocation for **100,000 zatoshis**, its merchant resolution, the decision's evaluation snapshot, and its event. The report now shows **100,000 credited**, **100,000 outstanding**, and **0 candidate** for that allocated output. The partially paid case remains open for further evidence.
6. Retry the same approval, then submit the same output against a second invoice. The retry adds nothing; the second invoice receives a conflict without learning the first invoice's private details.
7. Verify the tampered fixture and show invalid evidence with no allocation. Export the initial merchant report containing the inputs, findings, and decision references; the complete replay packet follows in M5.

**Development proof and release proof are separate:** simulated confirmation enables workflow tests, not a claim of observed chain inclusion. M3 replaces the simulated observer with a trusted live source for release validation. No production route or request field can create a trusted confirmation.

### Implementation defaults

- Retain FastAPI, SQLAlchemy/Alembic, PostgreSQL, the existing Rust/Glasspane wrapper, and Vue 3/TypeScript/Tailwind. Keep synchronous bounded verification for P0; do not introduce a queue or microservices.
- Keep receipt-result schema version 1 and the existing POC endpoint compatible. Add separate workflow/report contracts instead of overloading `VerificationReport.chain_state`.
- Provision merchant access through an operator CLI for the hackathon. No signup, email delivery, wallet authentication, or identity-verification product is required.
- Use a same-origin deployment: FastAPI serves the built Vue application and `/api`; Vite proxies `/api` in development. This removes a separate frontend-hosting dependency from P0. Vercel can remain a later hosting choice.
- Use one case per invoice snapshot in P0. Multiple approved outputs can accumulate on that invoice. Do not implement split allocations, allocation reversal, or reassigning an approved output.
- Default invoice policy: ten confirmations for credit, an observation no more than 60 seconds old at commit, exact memo binding, and no overpayment approval. These are explicit engineering defaults, stored with the invoice, not a guarantee against reorganization.
- Leave `unique_receiver_binding=false` in the public P0 workflow. No registry currently proves receiver uniqueness, so callers must not be able to assert it. Missing memo evidence remains reviewable but cannot bypass binding requirements.
- Operate the hackathon demo with public fixtures. Real customer onboarding remains gated on documented retention/deletion terms and deployment controls from the PRD; do not describe the demo as a production pilot.

## 2. Current foundation and remaining integration

| Implemented foundation | Remaining integration work |
|---|---|
| Stored invoice policies, authoritative balances, and historical evaluation snapshots | Preservation validated in PR #24; retain the final release revision’s evidence |
| Atomic merchant decisions, invoice locking, output uniqueness, retries, and chained events | Merged access integration and recovery preserve these guarantees; P4 browser acceptance remains |
| Encrypted optional receipt/raw-tx bundles, customer attribution/consent and persisted real verification | Selected reviewer disclosure validated across recovery in PR #24; P4 browser presentation remains |
| Offline and trusted RPC observers, refresh history, and later chain-review findings | Validate against an actual trusted node and retain the live approval trace |
| Merchant credentials, case grants, browser sessions and transaction authorization | Read/export enforcement validated across recovery in PR #24; actual-browser acceptance remains |
| Case create/detail/report/list routes and scoped claim writers | Retain separate detail/report contracts in frontend integration |
| Readiness tracks the packaged migration head; revisions through `0009` exist | Forward migration/recovery validated; confirm target-specific operator procedures |
| Recorded real-verifier, PostgreSQL workflow and grant/session/submission tests | Export/replay recovery recorded; collect browser/live and final release evidence |

Primary implementation references: [models](../apps/api/src/zecsolve/db/models.py), [rules](../apps/api/src/zecsolve/domain/rules.py), [API assembly](../apps/api/src/zecsolve/main.py), [verifier adapter](../apps/api/src/zecsolve/adapters/verifier.py), and [initial migration](../apps/api/migrations/versions/0001_initial_schema.py).

## 3. Ownership and feature tasks

Milestones are delivery checkpoints; each task below is one branch and one accountable owner. The dates in PRD §9 remain the delivery target, not estimates or completion evidence. Person numbers are the user's assignment slots; record the actual contributor and branch/PR when a task is claimed. Naming branches here does not create them or announce that work has started.

| Milestone | Current status | Delivery gate | PRD coverage |
|---|---|---|---|
| M1 | Backend complete; development Items 01–06 | Authenticated invoice/case/evidence through persisted real verification | P0-01, P0-02, P0-05, merchant portion of P0-06 |
| M2 | Backend complete; Item 07 uses simulated confirmation | Atomic merchant allocation, initial report, retries/conflicts/rollback | P0-03, P0-04, core P0-07 |
| M3 | Adapter implemented; M3.1 live evidence merged in PR #27 | Associate live node/approval evidence with the final release revision | P0-02, P0-04, P0-05 |
| M4 | Backend complete; M4.0–M4.5 merged | P4 browser integration/acceptance remains | Remaining P0-01 and P0-06 |
| M5 | Backend implemented and validated | P4 download/browser integration and full release still require their acceptance gates; live release requires M3.1 | P0-08 |
| M6 | Person 4 implementation/browser evidence complete locally; PR #26 published; review/CI/merge pending | M6.0–M6.6 integrated against the actual backend | P0-07 |
| M7 | Backend deployment/recovery and export/replay integration merged (PRs #17/#19/#24); evidence consolidation awaiting PR integration | Full M7.1/M7.2 and all preceding release gates | P0-09 and all acceptance gates |

### Ownership and coordination

| Owner | Accountable scope | Consumer boundary |
|---|---|---|
| Person 1 | Access/authentication, shared actor/schema foundation, grants, browser sessions | One shared authorization contract for every backend service and frontend session client |
| Person 2 | Scoped reports, disclosure projections, packet contract, replay and authorized export | Frontend/export reuse the same disclosure policy and versioned packet types |
| Person 3 | Case listing, customer submission backend, live validation, deployment and release | Submission services consume Person 1's access interfaces; deployment consumes Person 4's built app |
| Person 4 | All frontend source, shell, API client/types, merchant/customer/reviewer screens, styles, accessibility, build configuration and browser tests | Consume backend contracts; no backend contributor independently implements UI |

- Read [CONTRIBUTING.md](../CONTRIBUTING.md), fetch branches, inspect open PRs and check unpublished-PR branches before claiming work. Record the contributor, status and branch/PR; publish the task branch before implementation. Never treat this board as a remote lock.
- Start dependent branches from updated `main` only after their prerequisite PRs merge. Explicit fixture/requirements preparation may happen earlier, but does not satisfy integrated acceptance. Use the repo's merge-commit workflow.
- Person 1 owns shared authentication, `db/models.py` and migration-head changes. Others request prerequisite shared changes before coding against them; Person 1 does not take over their feature services. Extend the current migration head in order; do not reserve guessed revision numbers or create competing heads.
- Person 2 owns report/evidence/export disclosure projections. Person 3 owns evidence submission changes. Changes to a shared evidence module must be handed off after M4.4 merges, rather than edited concurrently.
- Coordinate and serialize integration edits to `main.py`, configuration, schema-generation registration, and CI. Each feature supplies its own contracts/tests; update the branch from `main` and regenerate affected outputs before merging. No two active tasks independently refactor these shared files.
- Person 4 owns frontend tests and package/build configuration. Person 3 owns deployment/CI wiring and backend static serving; agree the build-output and `/api` contract before M7.1 integration.
- Keep M1/M2 behavior, existing merchant bearer clients, historical hashes and the separate case-detail/report endpoints compatible. Adding browser roles must not change who can verify, resolve or allocate credit.

### Start order and status

`Ready` means prerequisites exist, not that work is claimed. `Waiting` means a listed merge/integration dependency is incomplete. `Externally blocked` means an operator-supplied dependency is missing. `Deferred` means the user has not resumed that scope. Add `In progress`, `In review`, and `Done` only with branch/PR and validation evidence.

M4.0–M4.5 and M5.0–M5.2 are merged. Person 1's handoffs are in [access.md](access.md), [grants.md](grants.md), and [sessions.md](sessions.md); Person 3's M4.4 handoff is [customer-submissions.md](customer-submissions.md). Person 2 has implemented scoped reports, packet contracts, replay and export; task validation and integration references are tracked below. Person 3's M7.1 backend preparation and M7.2 recovery/export integration are merged in PRs #17/#19/#24. Release evidence consolidation proceeds on `docs/m7-release-evidence`; full M7 completion still needs the listed integration gates.

Person 4's PR #12 supplies the initial frontend; PR #26 supplies the resumed M6 integration and browser evidence and awaits review/CI/merge. Fixtures may unblock dependent screens, but completion always requires the actual backend. M3.1 is independent external validation. M5 development and simulated tests may proceed while M3.1 is blocked; full live release cannot.

### Feature board

The links below lead to the scope and acceptance card for each branch. DEVELOPMENT.md retains each implementation's historical evidence; merged status is recorded here separately. The common PR/CI/merge gate still applies.

| Task | Owner | Branch | Prerequisites | Status |
|---|---|---|---|---|
| [M3.1 — Live validation](#m3-1) | Person 3 | `docs/m3-live-validation` | Operator-selected QuickNode public demo endpoint | Live acceptance evidence merged in PR #27 |
| [M4.0 — Access foundation](#m4-0) | Person 1 | `feat/m4-access-foundation` | Existing M1/M2 and M3 implementation on main | Done: PR #14 merged |
| [M4.1 — Grant lifecycle](#m4-1) | Person 1 | `feat/m4-case-grants` | M4.0 merged | Done: PR #15 merged |
| [M4.2 — Browser sessions](#m4-2) | Person 1 | `feat/m4-browser-sessions` | M4.1 merged | Done: PR #16 merged |
| [M4.3 — Case listing](#m4-3) | Person 3 | `feat/m4-case-listing` | Existing merchant case backend on main | Done: PR #13 merged |
| [M4.4 — Customer submissions](#m4-4) | Person 3 | `feat/m4-customer-submissions` | M4.2 merged, including the M4.0 persistence interfaces | Done: PR #18 merged |
| [M4.5 — Scoped reports](#m4-5) | Person 2 | `feat/m4-scoped-reports` | M4.2 and M4.4 merged | Done: PR #20 merged |
| [M5.0 — Packet contract](#m5-0) | Person 2 | `feat/m5-packet-contract` | M4.0 merged | Done: PR #21 merged |
| [M5.1 — Replay command](#m5-1) | Person 2 | `feat/m5-replay-case` | M5.0 merged | Done: PR #22 merged |
| [M5.2 — Authorized export](#m5-2) | Person 2 | `feat/m5-case-export` | M4.5 and M5.1 merged | Done: [PR #23](https://github.com/Kurisu-Labs/zecsolve/pull/23) merged |
| [M6.0 — Application foundation](#m6-0) | Person 4 | `feat/m6-frontend-integration` | Frontend explicitly resumed; existing workflow contracts | Implemented and locally validated; PR #26 published; review/CI/merge pending |
| [M6.1 — Browser access](#m6-1) | Person 4 | `feat/m6-frontend-integration` | Frontend resumed; M6.0 and M4.2 merged | Implemented and locally validated; PR #26 published; review/CI/merge pending |
| [M6.2 — Merchant workflow](#m6-2) | Person 4 | `feat/m6-frontend-integration` | Frontend resumed; M6.1 and M4.3 merged | Implemented and locally validated; PR #26 published; review/CI/merge pending |
| [M6.3 — Grant management](#m6-3) | Person 4 | `feat/m6-frontend-integration` | Frontend resumed; M6.2, M4.1 and M4.4 merged | Implemented and locally validated; PR #26 published; review/CI/merge pending |
| [M6.4 — Customer submission](#m6-4) | Person 4 | `feat/m6-frontend-integration` | Frontend resumed; M6.1 and M4.4 merged | Implemented and locally validated; PR #26 published; review/CI/merge pending |
| [M6.5 — Reviewer and export views](#m6-5) | Person 4 | `feat/m6-frontend-integration` | Frontend resumed; M6.1, M6.2, M4.5 and M5.2 merged | Implemented and locally validated; PR #26 published; review/CI/merge pending |
| [M6.6 — Browser acceptance](#m6-6) | Person 4 | `feat/m6-frontend-integration` | Frontend resumed; M6.2, M6.3, M6.4 and M6.5 merged | Implemented and locally validated; PR #26 published; review/CI/merge pending |
| [M7.1 — Deployment controls](#m7-1) | Person 3 | `feat/m7-deployment-controls` | Backend preparation can start on current main; completion requires M4.2 and M6.0 | Backend and TLS session preparation validated; browser integration pending |
| [M7.2 — Release rehearsal](#m7-2) | Person 3 | `docs/m7-release-evidence` | PR #24 merged for evidence consolidation; M7.1, M3.1, all M4/M5 tasks and M6.6 for full completion | Recovery/export integration merged in PRs #19/#24; evidence consolidation implemented, PR integration pending; full release waiting |

### Task cards

<a id="m3-1"></a>

#### M3.1 — Live validation

- **Owner:** Person 3. **Branch:** `docs/m3-live-validation`. **Status:** Live acceptance evidence merged in PR #27.
- **Prerequisites:** Met for this run: operator selected QuickNode’s public demo endpoint and the existing public fixture; no new payment required.
- **Goal:** Close the remaining trusted-chain release gate using the public historical fixture.
- **Owned code:** `docs/chain.md` validation procedure, `scripts/validate_live_chain.py` opt-in reproducibility harness, and sanitized release evidence; coordinate any adapter defect separately.
- **Exclusions:** No simulated result may satisfy this gate; no new payment, node provisioning, frontend, or unrelated RPC refactor.
- **Public interfaces:** Exercise the existing refresh and merchant resolve APIs with server-configured RPC settings; preserve observation-v1/v2 compatibility.
- **Acceptance checks:** Record actual node version/capabilities, bound raw transaction/network/block/confirmation data, freshness and policy eligibility, and a real merchant approval trace.
- **Validation evidence:** [Recorded run](chain.md#recorded-live-run) and [unchanged JSON](evidence/m3-live-f8a594f.json): clean `f8a594f`, October 12 13:23:24–13:23:30 UTC, Zebra 6.4.2, bound live confirmations, fresh eligible merchant approval and identical retries. See Item 22 in DEVELOPMENT.md. No RPC secrets retained. All cards also require the common definition of done below.

<a id="m4-0"></a>

#### M4.0 — Access foundation

- **Owner:** Person 1. **Branch:** `feat/m4-access-foundation`. **Status:** Done: PR #14 merged.
- **Prerequisites:** Existing M1/M2 and M3 implementation on main.
- **Goal:** Provide one shared access and persistence foundation for the remaining backend tasks.
- **Owned code:** `auth/`, shared workflow authorization, `db/models.py`, forward access migrations, and access contracts. Source paths in these cards are relative to `apps/api/src/zecsolve/` unless otherwise stated.
- **Exclusions:** No customer UI, packet implementation, grant/session HTTP lifecycle, or parallel identity model. Preserve existing merchant bearer credentials and historical hashes.
- **Public interfaces:** Publish the common actor/access context and transaction-time authorization interfaces, plus grant/session/consent/claim-attribution and retry references. Agree report/evidence/export permission vocabulary with Person 2; downstream services consume it.
- **Acceptance checks:** Migrations preserve existing rows, evidence decryption, audit/retry records, and merchant behavior; customer attribution does not require a fake merchant credential. Expiry/revocation and case scoping can be rechecked after waits; shared contract tests pass.
- **Validation evidence:** Shared contracts and transaction/persistence handoff: [access.md](access.md). Migration preservation, post-lock expiry, role isolation and merchant regressions are tested; see the development record and feature PR for final validation. All cards also require the common definition of done below.

<a id="m4-1"></a>

#### M4.1 — Grant lifecycle

- **Owner:** Person 1. **Branch:** `feat/m4-case-grants`. **Status:** Done: PR #15 merged.
- **Prerequisites:** M4.0 merged.
- **Goal:** Let merchants manage bounded customer/reviewer access to one owned case.
- **Owned code:** New grant schemas, services, API router, and focused tests; any shared model changes remain with Person 1.
- **Exclusions:** No UI, browser session exchange, evidence submission, or report projection implementation. Existing source labels and processing acknowledgements are not reviewer-sharing authorization.
- **Public interfaces:** `POST /api/cases/{id}/grants`, `GET /api/cases/{id}/grants`, and `DELETE /api/cases/{id}/grants/{grant_id}`. Reveal initial access codes once; subsequent metadata/replay must not redisclose reusable secrets.
- **Acceptance checks:** Creation, metadata inspection, expiry, and idempotent revocation work; reject foreign cases, overbroad selections, and evidence without sharing authorization. Customer/reviewer roles cannot manage grants. Report-only grants can work before M4.4; evidence grants require its consent records.
- **Validation evidence:** Pending: two-merchant/role, expiry/revocation, consent-selection, retry and secret-disclosure tests plus request/response examples. All cards also require the common definition of done below.

<a id="m4-2"></a>

#### M4.2 — Browser sessions

- **Owner:** Person 1. **Branch:** `feat/m4-browser-sessions`. **Status:** Done: PR #16 merged.
- **Prerequisites:** M4.1 merged.
- **Goal:** Exchange an initial merchant or grant code for revocable browser access.
- **Owned code:** Session authentication, session router/service, Origin/CSRF handling, and relevant configuration/tests.
- **Exclusions:** No frontend login screen, localStorage token scheme, signup, email delivery, or customer role expansion.
- **Public interfaces:** `POST`, `GET`, and `DELETE /api/session`; authenticated scope and CSRF usage documented for Person 4. Preserve existing merchant bearer clients.
- **Acceptance checks:** Secure HttpOnly SameSite cookies, trusted Origin and CSRF checks protect state-changing cookie requests. Sessions last at most eight hours and never exceed underlying expiry; revocation takes effect on subsequent requests. Logout, invalid exchange, expiry during waits, and role denial pass.
- **Validation evidence:** Pending: session/security matrix, bearer compatibility regressions, and browser-client contract examples. All cards also require the common definition of done below.

<a id="m4-3"></a>

#### M4.3 — Case listing

- **Owner:** Person 3. **Branch:** `feat/m4-case-listing`. **Status:** Done: PR #13 merged. No claim of M4 completion.
- **Prerequisites:** Existing merchant case backend on main.
- **Goal:** Supply merchant dashboard summaries without requiring full reports.
- **Owned code:** Case-list schema and focused additions to case router/service/tests.
- **Exclusions:** No grants, claim writes, shared authentication changes, frontend, or detail/report replacement. No schema migration is planned.
- **Public interfaces:** `GET /api/cases` with cursor pagination and optional state filter; preserve existing `GET /api/cases/{id}` and `/report`.
- **Acceptance checks:** Pagination has deterministic ordering with an ID tie-breaker; filters, empty results and invalid cursors are handled; credentials are rechecked and foreign cases/private evidence never appear.
- **Validation evidence:** [Item 09](DEVELOPMENT.md#item-09--merchant-case-listing-m43) records 14 real-PostgreSQL listing tests, 16 contract/cursor tests and full backend checks. [API guide and sample response](cases.md#list-merchant-cases), [query schema](../contracts/case-list-query.schema.json), and [list schema](../contracts/case-list.schema.json) are the Person 4 handoff. No frontend, authentication foundation or migration edits were included. All cards also require the common definition of done below.

<a id="m4-4"></a>

#### M4.4 — Customer submissions

- **Owner:** Person 3. **Branch:** `feat/m4-customer-submissions`. **Status:** Done: PR #18 merged.
- **Prerequisites:** M4.2 merged, including the M4.0 persistence interfaces.
- **Goal:** Accept scoped customer claims and evidence with honest attribution and recorded disclosure consent.
- **Owned code:** Claim writer/router/contracts and submission changes to evidence service/router; new audit payload versions and focused tests. Request additional shared schema work from Person 1 before using it.
- **Exclusions:** No grant/session implementation, reviewer report projection, frontend, allocation, or automatic verification.
- **Public interfaces:** `POST /api/cases/{id}/claims` and the extended evidence submission API accept authorized merchants/customers. Record actor/grant, processing permission, disclosure version/time, and reviewer-sharing choice; sharing defaults false. Customer responses are minimal acknowledgements.
- **Acceptance checks:** Exact evidence bytes remain encrypted; claim/evidence links stay within the case. Consent, version/event and retry outcome commit atomically; failed writes roll back. Same-key replay adds nothing; terminal cases, foreign IDs, revoked sessions and attempts to verify/approve are rejected. Existing merchant inputs remain supported.
- **Validation evidence:** [Customer submission guide](customer-submissions.md) and [Item 14](DEVELOPMENT.md#item-14--customer-claims-and-encrypted-evidence-m44) record the contracts, 17 contract/audit tests and 20 PostgreSQL/HTTP submission tests, with the full validation results. P2 consumes explicit consent/attribution; P4 consumes minimal acknowledgements. All cards also require the common definition of done below.

<a id="m4-5"></a>

#### M4.5 — Scoped reports

- **Owner:** Person 2. **Branch:** `feat/m4-scoped-reports`. **Status:** Done: PR #20 merged; M4.2/M4.4 merged.
- **Prerequisites:** M4.2 and M4.4 merged.
- **Goal:** Expose only explicitly selected report fields and consented evidence to reviewers.
- **Owned code:** Role projections, report service/router integration, authorized evidence-read interfaces, and disclosure tests. Person 1 retains shared auth/model ownership; Person 3 retains evidence submission.
- **Exclusions:** No alternate permission system, frontend, exporter, or broadening of case detail access. Do not serialize the whole merchant report and strip a few fields afterward.
- **Public interfaces:** Keep merchant `/report` compatible and add explicit reviewer response types/disclosure scope. Existing evidence metadata reads and a scoped `GET /api/cases/{id}/evidence/{evidence_id}/content` enforce the same allowlist/consent policy; return permitted original components, never ciphertext or secrets.
- **Acceptance checks:** The route-wide matrix covers two merchants, a customer, report-only reviewer, and evidence/export reviewer. Guessed IDs, unconsented or unselected evidence, foreign allocation details, revoked/expired grants, and unauthorized mutations are denied; allowed report fields remain useful.
- **Validation evidence:** [Scoped report handoff](scoped-reports.md) documents explicit response fields and evidence reads. Nine PostgreSQL/HTTP scenarios cover the five-role matrix, consent/selection, foreign conflicts, decision disclosure, expiry and revocation; see [Item 16](DEVELOPMENT.md#item-16--scoped-reviewer-reports-m45). All cards also require the common definition of done below.

<a id="m5-0"></a>

#### M5.0 — Packet contract

- **Owner:** Person 2. **Branch:** `feat/m5-packet-contract`. **Status:** Done: PR #21 merged.
- **Prerequisites:** M4.0 merged.
- **Goal:** Freeze the common packet format consumed by both exporter and replay.
- **Owned code:** Packet schemas, integrity/canonicalization contract, public/synthetic complete and scoped fixtures, and schema tests.
- **Exclusions:** No database exporter, permission implementation, CLI execution, fabricated live evidence, or revision of historical hashes.
- **Public interfaces:** `CasePacketV1`: exact encoded inputs/hashes, invoice/policy, provenance, observations, verifier/rules versions, evaluation/allocation context, decisions/events, integrity manifest, and explicit disclosure/replay scope.
- **Acceptance checks:** Complete and limited fixtures validate; original-file and decoded-transaction hashes stay distinct; omitted/redacted inputs and foreign conflicts are explicit. Current and historical supported record formats have contract coverage.
- **Validation evidence:** [Packet contract](packets.md), [public/synthetic fixtures](../fixtures/packets/README.md) and [Item 17](DEVELOPMENT.md#item-17--packet-contract-m50) record generated schema/hash profile and 13 passing contract tests. GitHub access was restored; PR #21 merged after all CI passed. All cards also require the common definition of done below.

<a id="m5-1"></a>

#### M5.1 — Replay command

- **Owner:** Person 2. **Branch:** `feat/m5-replay-case`. **Status:** Done: PR #22 merged.
- **Prerequisites:** M5.0 merged.
- **Goal:** Reproduce a packet locally without treating historical observation claims as fresh chain trust.
- **Owned code:** Replay library/CLI, historical evaluator dispatch, and replay fixtures/tests.
- **Exclusions:** No database export, network lookup, arbitrary executable/version installation, UI, or merchant credit mutation.
- **Public interfaces:** Local `replay-case` command reports cryptographic recovery, historical rules/arithmetic, integrity and unsupported/missing/external context separately.
- **Acceptance checks:** Real fixture recovery and historical calculations reproduce; one-byte tampering fails integrity; unsupported versions and scoped omissions do not claim full success. Packet content cannot trigger arbitrary fetches or code execution.
- **Validation evidence:** [Replay guide](packets.md#offline-replay-m51) and [recorded CLI outputs](../fixtures/packets/replay-results.json) cover all five outcomes with file hashes; 20 replay tests pass locally. See [Item 18](DEVELOPMENT.md#item-18--offline-replay-m51). All cards also require the common definition of done below.

<a id="m5-2"></a>

#### M5.2 — Authorized export

- **Owner:** Person 2. **Branch:** `feat/m5-case-export`. **Status:** Done: [PR #23](https://github.com/Kurisu-Labs/zecsolve/pull/23) merged.
- **Prerequisites:** M4.5 and M5.1 merged.
- **Goal:** Export an authorized, internally consistent packet that the local replay command can consume.
- **Owned code:** Export snapshot assembler/router, shared projection consumption, and export/replay integration tests.
- **Exclusions:** No independent permissions, receipt redaction presented as complete replay, foreign case disclosure, or frontend download screen.
- **Public interfaces:** `GET /api/cases/{id}/export` returns `CasePacketV1`; reviewer export requires an explicit additional grant. Reuse M4.5 disclosure rules and M5.0 types.
- **Acceptance checks:** Concurrent approval cannot mix snapshots; reauthorization blocks revoked access. Permitted exact inputs/history survive export and replay; denied/omitted evidence is excluded and marked. Valid, tampered and scoped cases pass their expected outcomes.
- **Validation evidence:** [Export guide](packets.md#authorized-export-m52), `test_exports.py` and [Item 19](DEVELOPMENT.md#item-19--authorized-snapshot-export-m52) record the permission/consent matrix, concurrent snapshot proof, exact-input/negative replay and sanitized packet boundaries. All cards also require the common definition of done below.

<a id="m6-0"></a>

#### M6.0 — Application foundation

- **Owner:** Person 4. **Branch:** `feat/m6-frontend-integration`. **Status:** Implemented and locally validated; PR #26 published; review/CI/merge pending. See [frontend evidence](frontend.md).
- **Prerequisites:** Frontend explicitly resumed; existing workflow contracts.
- **Goal:** Establish the Vue 3/TypeScript/Tailwind app and reusable frontend contracts.
- **Owned code:** New `apps/web` source, routing, components, styles, frontend package/build configuration, generated API client types and frontend tests.
- **Exclusions:** No backend permission/business logic, unlabelled simulated data, or unfinished backend endpoint represented as working.
- **Public interfaces:** Generate client types from backend OpenAPI; use same-origin `/api` with the Vite development proxy. Provide exact integer-zatoshi formatting, shared loading/error handling, and independent receipt/chain/case/business status displays.
- **Acceptance checks:** Type checking/build pass; routing and explicit API fixtures work; money conversion is exact and shared components support keyboard access and responsive layouts. Document the build output contract for Person 3.
- **Validation evidence:** Pending: build/typecheck/component results and fixture-backed screenshots; not actual-backend feature acceptance. All cards also require the common definition of done below.

<a id="m6-1"></a>

#### M6.1 — Browser access

- **Owner:** Person 4. **Branch:** `feat/m6-frontend-integration`. **Status:** Implemented and locally validated; PR #26 published; review/CI/merge pending. See [frontend evidence](frontend.md).
- **Prerequisites:** Frontend resumed; M6.0 and M4.2 merged.
- **Goal:** Connect all three roles to the browser session contract.
- **Owned code:** Frontend access-code entry/exchange, session state, protected navigation, logout, expiry/revocation screens and tests.
- **Exclusions:** No backend session implementation, signup, localStorage credentials, or query-string access codes.
- **Public interfaces:** Consume session APIs and documented CSRF mechanism. Accept manual/fragment codes, strip them after exchange, and render role-appropriate navigation.
- **Acceptance checks:** Session restoration/logout and invalid/expired/revoked access work against the actual backend; codes do not persist in URLs or localStorage; forbidden views and stale sessions recover safely.
- **Validation evidence:** Pending: actual-backend session scenarios and frontend access/security checks. All cards also require the common definition of done below.

<a id="m6-2"></a>

#### M6.2 — Merchant workflow

- **Owner:** Person 4. **Branch:** `feat/m6-frontend-integration`. **Status:** Implemented and locally validated; PR #26 published; review/CI/merge pending. See [frontend evidence](frontend.md).
- **Prerequisites:** Frontend resumed; M6.1 and M4.3 merged.
- **Goal:** Deliver the merchant invoice-to-decision workflow using existing services.
- **Owned code:** Frontend case list, invoice/case creation, evidence upload/selection, verification, report/balance display, decision forms and tests.
- **Exclusions:** No new backend endpoints, grants UI, export integration, automatic approval, or floating-point money conversion.
- **Public interfaces:** Consume existing invoice/case/evidence/verify/report/resolve APIs and the M4.3 list contract. Keep one retry key per pending action and send the reviewed case version.
- **Acceptance checks:** Merchant completes the flow against the actual backend; retries after response loss do not duplicate work; stale versions require refreshed review. Partial payments, conflicts, tamper rejection, missing evidence and unavailable/insufficient chain evidence are accurately displayed.
- **Validation evidence:** Pending: backend-connected merchant browser scenarios and screenshots; simulated confirmations visibly labelled. All cards also require the common definition of done below.

<a id="m6-3"></a>

#### M6.3 — Grant management

- **Owner:** Person 4. **Branch:** `feat/m6-frontend-integration`. **Status:** Implemented and locally validated; PR #26 published; review/CI/merge pending. See [frontend evidence](frontend.md).
- **Prerequisites:** Frontend resumed; M6.2, M4.1 and M4.4 merged.
- **Goal:** Let merchants manage access and allowed disclosure from a case.
- **Owned code:** Frontend grant creation/list/revocation, field/evidence selection, export permission controls and tests.
- **Exclusions:** No backend permissions/consent changes, silent sharing defaults, or recovery of previously revealed codes.
- **Public interfaces:** Consume grant metadata/create/revoke APIs and the available consent metadata. Display newly created codes once and explain revocation/download limits.
- **Acceptance checks:** Create/revoke customer and reviewer access against the backend; unconsented evidence cannot be selected successfully; report/evidence/export permissions remain distinct; errors and expired/revoked states are visible.
- **Validation evidence:** Pending: backend-connected grant-management scenarios, consent restriction checks and screenshots. All cards also require the common definition of done below.

<a id="m6-4"></a>

#### M6.4 — Customer submission

- **Owner:** Person 4. **Branch:** `feat/m6-frontend-integration`. **Status:** Implemented and locally validated; PR #26 published; review/CI/merge pending. See [frontend evidence](frontend.md).
- **Prerequisites:** Frontend resumed; M6.1 and M4.4 merged.
- **Goal:** Provide the scoped disclosure, consent and submission experience.
- **Owned code:** Frontend disclosure/consent, claim/evidence form, minimal acknowledgement and tests.
- **Exclusions:** No merchant/reviewer report access, verification/approval controls, or backend submission changes.
- **Public interfaces:** Consume claim/evidence submission APIs and their customer acknowledgements; optional missing evidence stays explicit; reviewer sharing starts unchecked.
- **Acceptance checks:** Customer submits with recorded consent against the backend; retry/validation/expired-access paths work; no unrelated evidence or merchant actions appear, including on direct navigation.
- **Validation evidence:** Pending: actual-backend submission and role-isolation browser results plus consent/acknowledgement screenshots. All cards also require the common definition of done below.

<a id="m6-5"></a>

#### M6.5 — Reviewer and export views

- **Owner:** Person 4. **Branch:** `feat/m6-frontend-integration`. **Status:** Implemented and locally validated; PR #26 published; review/CI/merge pending. See [frontend evidence](frontend.md).
- **Prerequisites:** Frontend resumed; M6.1, M6.2, M4.5 and M5.2 merged.
- **Goal:** Show reviewer disclosures and connect authorized downloads for reviewers and merchants.
- **Owned code:** Frontend reviewer report, selected evidence display, download controls, merchant export integration and tests.
- **Exclusions:** No client-only authorization, backend exporter/projection changes, or write controls for reviewers.
- **Public interfaces:** Consume scoped report/evidence and export APIs. Distinguish report-only from export-enabled access and label incomplete/scoped packets and proof limits.
- **Acceptance checks:** Granted information displays correctly against the backend; denied direct reads/downloads remain denied; authorized packets download; memo/notes render as text, never markup; merchant export is connected.
- **Validation evidence:** Pending: backend-connected reviewer/export matrix, text-rendering checks and screenshots. All cards also require the common definition of done below.

<a id="m6-6"></a>

#### M6.6 — Browser acceptance

- **Owner:** Person 4. **Branch:** `feat/m6-frontend-integration`. **Status:** Implemented and locally validated; PR #26 published; review/CI/merge pending. See [frontend evidence](frontend.md).
- **Prerequisites:** Frontend resumed; M6.2, M6.3, M6.4 and M6.5 merged.
- **Goal:** Close M6 with end-to-end proof across the three roles.
- **Owned code:** Frontend actual-backend browser suite, accessibility/responsive QA, UI evidence and frontend setup documentation; coordinate CI registration with Person 3.
- **Exclusions:** No mocked responses counted as end-to-end acceptance, live inclusion claim from simulated observers, or backend feature ownership transfer.
- **Public interfaces:** Exercise the shipped frontend and actual backend APIs; use only isolated explicitly labelled test confirmation composition.
- **Acceptance checks:** First slice, same-invoice retry, cross-invoice conflict, tampered/missing evidence, insufficient confirmation, stale decisions, consent, role restrictions, expiry/revocation and export pass. Keyboard, labelled errors, loading states and responsive checks pass.
- **Validation evidence:** Pending: browser/typecheck/build results, screenshots, revision/environment, and the UI evidence handoff to Person 3. All cards also require the common definition of done below.

<a id="m7-1"></a>

#### M7.1 — Deployment controls

- **Owner:** Person 3. **Branch:** `feat/m7-deployment-controls`. **Status:** Backend preparation merged in PR #17; full M7.1 remains incomplete pending Person 4 browser integration.
- **Prerequisites:** Backend preparation can start on current main; completion requires M4.2 and M6.0.
- **Goal:** Provide a bounded same-origin deployment of the backend and Person 4's built application.
- **Owned code:** `infra/`, Compose/ingress deployment configuration, backend static-serving integration, readiness/logging/limits and coordinated CI wiring.
- **Exclusions:** No frontend source/build-config edits owned by Person 4, private-customer pilot claim, live RPC substitute, or destructive database downgrade.
- **Public interfaces:** Consume Person 4's frontend build output contract; serve `/api` and app through TLS. Preserve packaged-head/encryption/verifier readiness and separate chain capability.
- **Acceptance checks:** Runtime validation confirms TLS, correct cookie deployment, request/rate and CPU/memory limits, secret-safe logs, same-origin app/API serving and disabled public POC. An RPC outage does not masquerade as receipt failure.
- **Validation evidence:** [Deployment guide](deployment.md) and [Item 13](DEVELOPMENT.md#item-13--m71-backend-deployment-preparation) record 19 boundary tests, full native checks and ten actual-container acceptance groups. The separate deployment CI workflow repeats TLS session/cookie/Origin/CSRF, serving, ingress/resource limits, readiness outage recovery and log-redaction checks. The current frontend build is consumed without frontend-source changes. Full browser workflow/accessibility evidence remains pending; configuration parsing alone is insufficient. All cards also require the common definition of done below.

<a id="m7-2"></a>

#### M7.2 — Release rehearsal

- **Owner:** Person 3. **Branch:** `docs/m7-release-evidence` (follows `test/m7-release-rehearsal` and `test/m7-export-recovery`, merged in PRs #19/#24). **Status:** Evidence consolidation implemented; PR review/merge pending. Full release remains waiting.
- **Prerequisites:** M4.5/M5.0–M5.2 and the PR #19/#24 recovery/export integration are merged, enabling evidence consolidation without RPC. M7.1, M3.1, all M4/M5 tasks and M6.6 are required for full completion.
- **Goal:** Assemble reproducible release acceptance and recovery evidence. The current documentation slice maps A-01–A-15 to attributable runs, retains sanitized recovery evidence, documents repeatable offline demos and identifies outstanding gates/owners.
- **Owned code:** Current slice: `docs/release-evidence.md`, `docs/evidence/`, status references and appended development evidence. The existing `scripts/check_recovery.py`, `scripts/recovery_*.py` and regression checks remain P3-owned and unchanged in this slice. Person 4 supplies browser results and UI screenshots.
- **Exclusions:** No assumed discovery results, automatic outreach, skipped gate marked passed, production pilot claim, or mutation of historical DEVELOPMENT.md results.
- **Public interfaces:** Use existing workflow/export/replay/deployment interfaces; collect team-provided discovery/submission evidence and preserve attribution.
- **Acceptance checks:** For this slice, every A-ID links to a recorded run and specific scenario or explicit outstanding requirement; source artifact identity, local documentation links and demonstrated command outcomes are checked; stale status references are corrected without rewriting history. For full M7.2, migration, restart/lost-response recovery and encrypted restore pass. At every checkpoint, exact permitted bytes/history, balances and authorization survive; merchant packets reproduce with the packaged offline CLI, reviewer packets remain limited, and tampering fails. Restored revocation denies future reads/exports. All A-01–A-15 rows must have attributable evidence and required gates pass for full completion. Missing live validation or deferred frontend keeps full release incomplete. Document limits and recovery without losing accepted allocations.
- **Validation evidence:** [Backend recovery procedure and acceptance matrix](recovery.md) and [Item 15](DEVELOPMENT.md#item-15--m72-backend-recovery-rehearsal) record forward migrations, process/database restarts, lost-response retries, encrypted fresh-database restore and restored invariants: 19 actual-container groups, 211 PostgreSQL tests and six archive tests passed locally. The native subprocess timeout limitation is recorded explicitly. Combined deployment/recovery CI emits a sanitized revision/time/environment report. PR #19 merged. PR #24 merged the export/replay integration with 24 container groups and complete Linux suites, recorded in [Item 20](DEVELOPMENT.md#item-20--m72-exportreplay-recovery-integration). The [release evidence index](release-evidence.md) retains the sanitized CI report and scenario mapping; [Item 21](DEVELOPMENT.md#item-21--m72-release-evidence-consolidation) records this documentation validation. Live, UI and team-supplied release artifacts remain separate gates. All cards also require the common definition of done below.

### Definition of done

A task card is the handoff: owner, goal, branch, prerequisites, owned code, exclusions, public interfaces, acceptance checks, and validation evidence are mandatory. Update status/claim fields without rewriting historical results. Do not mark a task complete merely because its branch exists, its code compiles, or its implementation was pushed.

A feature is **Done** only when all of the following hold:

1. Its behavior and negative-path acceptance checks pass, including actual-backend integration where required.
2. Required repository checks pass: `make test` and `make lint` for application changes; `make test-db` on disposable PostgreSQL for database/migration/allocation changes and the task's database-backed authorization/submission scenarios. Regenerate changed published contracts with `make schema` and check their diff. Frontend work additionally passes its typecheck/build and relevant component/browser checks; Person 4 establishes those commands in M6.0.
3. Documentation and contracts match the implementation. A documentation-only task checks content, local links and `git diff --check`; it does not invent application-test results.
4. Evidence records commands/scenarios, actual outcomes, revision, environment, UTC timestamp and PR. Public/synthetic/simulated/live material is identified explicitly; no secrets or customer evidence enter the repo.
5. The final diff is reviewed, CI passes and the PR merges into `main`. Follow CONTRIBUTING.md for merge commits and branch cleanup; no forced or direct-to-main integration.

Task completion does not imply milestone or release completion. M4 needs the full route-wide role/consent matrix; M5 needs authorized export/replay and concurrency integrity; M6 needs the actual-backend browser gate; M7 needs all required release evidence, including M3.1 and resumed/completed M6. An acceptance row with an explicit incomplete outcome is useful tracking, not a passed release gate.


### Milestone requirements

The following retained requirements describe behavior and acceptance, including completed M1/M2 work. Use the task board above to select new work; do not restart completed milestones.

### M1 — authenticated invoice to persisted verification

**Application structure:** keep route handlers thin. Add `api/` routers, `services/` workflow/report functions, `auth/` dependencies, and workflow schemas under the existing Python package. Reuse `domain/` for pure rules and `adapters/` for bounded external work. A SQLAlchemy session belongs to one request/service unit of work; never share sessions across threads.

**Identity:** introduce principals tied to a merchant, hashed high-entropy credentials with expiry/revocation, and an operator provisioning command. Use opaque random credentials, not the shared POC token, for workflow access. Return the bootstrap credential once; store only its digest. Derive merchant/actor identity server-side on every request. An authenticated request for an inaccessible case or invoice returns 404 without revealing its existence.

**Invoice:** accept integer `expected_zat`, mainnet network, supported shielded pool, receiver address, optional memo text, and expiry. Normalize the receiver in Rust using the already-pinned `zcash_address` dependency via a separate bounded `normalize-address` mode; preserve the current verification CLI invocation. Reject mismatched network, invalid addresses, or an address lacking the requested receiver. Never accept client-supplied normalized bytes as authoritative. Encode memo text as UTF-8, reject values over 512 bytes, and right-pad to 512 bytes; preserve the original text and exact comparison bytes. Null means no expected memo.

Create invoice and immutable policy snapshot together. Hash a deterministic representation of the exact invoice terms and policy reference. A new invoice's policy is fixed at creation. Retain unsupported historical rows for inspection; do not invent missing policies for them or allow them to receive credit until explicitly reviewed.

**Case:** create a merchant-owned case against that invoice; enforce uniqueness of `invoice_id` for this P0 workflow. Record a `CASE_OPENED` event. Claims are optional assertions with a server-derived claimant role and principal/grant reference.

**Evidence:** save one bundle per submission, with an optional receipt and optional raw transaction. A bundle is still a real submitted record when a component is absent; it does not fabricate evidence. Preserve original UTF-8 strings/bytes and their hashes separately from the decoded raw-transaction hash. Reuse the current request/body and per-component size limits.

Store encrypted bundle content in PostgreSQL `BYTEA`, with metadata and an opaque storage reference. This lets metadata and content commit together without an object-store cleanup workflow. Use the `cryptography` library's AES-GCM, a fresh 96-bit nonce per encryption, a configured 256-bit secret key, and associated data binding merchant, case, evidence ID, and payload version. Persist key ID, nonce, and ciphertext; keep key material outside the database and out of logs. Enforce nonce uniqueness per key ID. Follow the [library's authenticated-encryption API](https://cryptography.io/en/stable/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM).

This protects original evidence blobs; existing invoice fields and recovered result records still require encrypted database volumes/backups and restricted database access. Do not claim application-level encryption covers every field.

**Verification:** authorize before loading/decrypting a bundle. Run `VerifierAdapter` outside any row-locking transaction, sharing the existing concurrency limiter across POC and workflow verification. Reauthorize when persisting, and reject attaching evidence from another case. Persist the complete immutable verifier result, an initial chain observation, an evaluation, and a case event. A `NONE`, `UNSUPPORTED`, `UNAVAILABLE`, or `ERROR` result is still a recorded attempt with its own reason; it is not an allocation.

For expensive verification retries, check for a completed idempotency result before running Rust and claim the key again in the short persistence transaction. Concurrent executions may perform the bounded read-only verification twice, but only one attempt/event is persisted for that key; the loser returns the recorded result. Do not hold database locks while waiting for the subprocess. A new key permits a deliberate new attempt after a technical failure.

**Gate:** an authenticated integration test creates invoice/case/evidence, calls the real Rust verifier, and reads the expected unapproved balances from the report. Another merchant cannot obtain those records. The offline observer produces unavailable status and blocks approval.

### M2 — merchant-approved allocation and reasoned report

Implement the resolution protocol in §5 before adding UI approval controls. Introduce typed resolution actions: `APPROVE_OUTPUT`, `REQUEST_EVIDENCE`, `REJECT_EVIDENCE`, and `CLOSE_UNRESOLVED`. Every action requires a reason; approval/rejection references a verification from the same case.

Extend the pure evaluation boundary with typed policy and chain-observation inputs, an injected evaluation time, and explicit freshness/confirmation findings. Increment `RULES_VERSION` for this behavior change and preserve the previous implementation for replay. Keep the returned balance fields and multi-finding behavior. A chain observation may be `CONFIRMED` but still below the invoice's required confirmation count; report that distinction instead of rewriting it as unconfirmed.

Add one report assembler used by `GET /api/cases/{id}`, the future UI, and the export service. It must show invoice terms, case version/state, claims as assertions, per-attempt verification/observation results, current approved balance, the selected candidate projection, decision history, and evidence provenance. Historical decision snapshots and current balances must be labeled separately.

The local demo harness must call the same routes/services as normal operation, use a disposable database/schema, run the real fixture verifier, and label injected observations `source_kind=SIMULATED`. Simulated observers and the policy permitting them exist only in test/demo composition, not in the deployed ASGI app or a public configuration toggle. The deployed app rejects simulated observations for credit even if such rows are present.

**Gate:** all seven first-slice steps in §1 pass, plus same-invoice concurrent retries, different-output concurrent approvals, and rollback after an injected event-write failure. No orphan resolution or allocation may survive a failed transaction.

### M3 — trusted live confirmation and negative paths

Implement a `ChainObserver.observe(network, txid, expected_raw_tx_sha256)` port. Keep an offline implementation and add a read-only Zebra-compatible JSON-RPC implementation using a server-configured endpoint. Promote the existing HTTP client dependency to runtime and use bounded timeouts/response sizes. Do not accept URLs, credentials, or confirmation assertions from customer input.

Use `getrawtransaction` with verbose output for the verified transaction ID; compare the returned decoded transaction hash with the verified raw bytes. Require correct network from `getblockchaininfo`, a current/synced source, and best-chain inclusion before returning a confirmed observation. Use the containing block's `getblockheader` result to verify its height/hash and current best-chain confirmations. Preserve source ID, observed time, transaction binding, block data, and the sanitized relevant response fields. Zebra documents these fields and their mempool/side-chain distinctions in its [transaction response](https://zebra.zfnd.org/internal/zebra_rpc/client/struct.TransactionObject.html), [block-header response](https://zebra.zfnd.org/internal/zebra_rpc/methods/struct.BlockHeaderObject.html), and [chain-info response](https://zebra.zfnd.org/internal/zebra_rpc/methods/struct.GetBlockchainInfoResponse.html).

The adapter must verify the selected node's actual response format during integration rather than treating Rust documentation field names as JSON field names. Record the tested node version and endpoint capabilities. Configuration remains a deployment dependency. M3.1 records the operator-selected QuickNode public demo source; an ongoing deployment must select and validate its own operating configuration.

- No RPC configuration, timeouts, authentication failures, malformed/missing fields, unsynced source, or ambiguous lookup failure → `UNAVAILABLE`, with a diagnostic reason.
- A supported response showing mempool or side-chain placement → `UNCONFIRMED`; a “not found” response alone is not a receipt-invalid result.
- Best-chain inclusion → `CONFIRMED` with observed count; credit additionally requires the stored policy threshold and freshness.
- Raw-byte or network mismatch → untrusted/unavailable observation with a binding failure reason; preserve the independent receipt result.

Refresh the observation before every new credit decision, outside the database lock transaction; recheck its age after locks are acquired. Do not keep using an older successful observation when the refresh fails. If a reorganization is observed later, retain the original approval record, flag the case for review, and block additional credit based on the invalidated observation. Automatic reversal is outside P0.

Use HTTPS for remote RPC, allow plain HTTP only for explicitly configured local/private infrastructure, disable redirects, and store credentials as secrets. A chain lookup discloses a transaction ID to that provider, never the receipt OCK or memo; disclose this in the case consent/help text.

**Gate:** run the historical fixture through the workflow with a real configured node and record the returned chain evidence, then approve using a merchant credential. Run adapter tests for insufficient confirmations, stale observations, missing transaction, wrong network/raw bytes, side chain, timeout, and request-supplied confirmation spoofing. Live access is required before marking the release credit path complete.

### M4 — customer/reviewer access and consent

Add merchant-created, expiring, revocable case grants. Customer grants permit claim/evidence submission and a minimal acknowledgement; they do not expose all case evidence or permit verification/approval. Reviewer grants permit the selected report fields and an explicit allowlist of evidence bundle IDs, with export enabled only when separately granted.

For browser access, exchange the initial access code for a server-side session in an HttpOnly, Secure, SameSite cookie; enforce trusted Origin plus CSRF protection for state-changing cookie-authenticated requests. Use an eight-hour session maximum and cap it at credential/grant expiry. Recheck the underlying credential/grant on every request so revocation also invalidates active sessions. Use a fragment or manual entry for the initial grant code; strip it after exchange and never store it in localStorage or query-string logs.

Consent version 1 records the submitting principal/grant, case/evidence, disclosure text version, time, permission for the merchant to process the bundle, and whether the bundle may be shared with reviewers. Default reviewer sharing to false. A merchant cannot grant a reviewer evidence lacking the required sharing authorization. Already-public fixtures are labeled as public source material, not customer consent.

Build explicit response projections by role; do not serialize the ORM case object and remove a few fields afterward. Recipient/memo fields, claims, other reviewers, decision reasons, and other submitted evidence can all reveal information. Default reviewer views to selected information only. Redact cross-merchant allocation conflicts to an opaque conflict indicator.

**Gate:** test two merchants, a customer grant, a report-only reviewer, and an evidence/export reviewer against every route. Include expired/revoked grants and sessions, unconsented evidence, guessed IDs, overbroad evidence IDs, direct download/export attempts, and memo markup injection. Explain that revocation cannot retract downloaded receipt copies.

### M5 — replayable export

Implement `CasePacketV1` and a local `replay-case` command. Build the packet from a consistent database snapshot, not separately timed queries that mix balances and decisions. Reuse the role projections from M4.

The packet contains the PRD §6.5 materials: invoice/policy, claims, exact receipt/raw transaction bytes with encodings/hashes, provenance and historical observations, verifier result and dependency revision, evaluation/rules version and owned allocation inputs, resolutions, and replayable event payloads. Embed binary content as base64; distinguish original-file hashes from decoded raw-transaction hashes. Include an integrity manifest and the report's data/disclosure mode.

Replay uses only bundled bytes and recognized verifier/rules versions. It does not fetch arbitrary URLs, execute code from a packet, or promote historical observations into fresh confirmation. Report separate outcomes for cryptographic recovery, arithmetic/rules reproduction, integrity, and assertions that cannot be independently established. Preserve access to the old rules version when the current one changes.

Use a deterministic JSON serialization profile for project-produced hashes: sorted object keys, compact separators, UTF-8, no floats/NaN, normalized UTC timestamps, and byte strings encoded explicitly. Document the profile version; do not claim general cross-language canonical JSON support without proving it.

For a cross-merchant conflict, include only a scoped assertion that the output was allocated elsewhere, never the foreign invoice/merchant record. Mark conflict truth as an external assertion and the packet `replay_scope=SCOPED`. Evidence omission/redaction must produce a limited report with explicit missing inputs, not a false full-replay success.

**Gate:** export/replay a valid approved case and the tampered case, modify one byte and observe integrity failure, and test missing/unsupported replay versions. Verify snapshot consistency during a concurrent approval and ensure all role/consent restrictions also apply to exports.

### M6 — Vue user flows

Create the frontend in `apps/web` using the established Vue/TypeScript/Tailwind choice. Generate TypeScript API types from OpenAPI after M2 freezes the first workflow contract. Start with a merchant case page; add the customer/reviewer views after their projections exist.

- **Merchant:** enter invoice terms, open/view a case, upload/select evidence, run verification, inspect independent statuses/balances, approve with a reason, request more evidence, reject evidence, close unresolved, manage grants, and download an authorized report/packet.
- **Customer:** review disclosure text, consent, submit a claim and optional receipt/raw transaction, and receive an acknowledgement without exposure to other evidence.
- **Reviewer:** inspect explicitly shared report sections/evidence, understand proof limits, and export only when granted. No merchant write actions are shown.
- Render ZEC from integer zatoshis using exact string conversion. Keep raw integer values in API calls and distinguish credited, outstanding, candidate, and projected balances.
- Approval controls reflect server eligibility but never replace server checks. Use one persistent idempotency key for a pending action, disable duplicate clicks, and recover the same outcome after a lost response. Refresh on a stale case version.
- Display receipt, chain, case, and business status independently, including simulated-source labels. Render memo/notes as text, with keyboard-accessible forms, labeled errors, loading states, and visible unavailable/unsupported states.

**Gate:** browser tests exercise the first slice, same-invoice retry, cross-invoice conflict, tamper rejection, missing receipt, below-threshold confirmation, and customer/reviewer restrictions against the actual backend. Isolated test observations must be visibly labeled.

### M7 — release, controls, and evidence

Bundle the Vue build with the existing unprivileged backend image, preserve migration-before-start behavior, and provide a same-origin TLS ingress. Keep the public POC verifier disabled in the release environment; grant access only to the workflow routes. Add ingress request/rate limits and container CPU/memory limits while retaining the bounded verifier adapter.

Readiness must check the actual packaged migration head, executable availability, and evidence-encryption configuration. Expose chain-observer availability as a separate capability so an RPC outage does not falsely claim verification failure or erase usable reports. Log correlation IDs, durations, sanitized reason codes, and allocation-conflict counts; exclude tokens, receipt content, RPC credentials, and recovered memo/receiver data.

Rehearse migrations on a disposable copy, verify database encryption/backups and restore of encrypted evidence with the correct external key, and test recovery after a lost response and application restart. Roll back application images only when schema-compatible; do not downgrade away accepted allocations. Disable new approvals if rollback cannot preserve invariants.

Capture commands/results with revision, environment, and time. Record the three demo scenarios, export replay, known limitations, and live chain validation. Conduct the PRD's two discovery conversations and record actual results, including negative feedback; this plan does not authorize contacting anyone automatically.

**Gate:** all P0 acceptance rows have evidence or an explicit incomplete status. Keep the October 12 submission target and October 13 contingency window from the PRD; lack of live confirmation means the full credit path is not release-complete, even if the fixture demonstration works.

## 4. Data, interface, and migration changes

### Persisted additions

Revisions `0001`–`0009` already exist. Person 1 owns the access foundation migrations and coordinates any later database additions. Extend the current Alembic head with forward revisions; never rewrite an applied migration or independently create competing heads. The table records required invariants across implemented and remaining records, not a request to recreate M1/M2 tables.

| Addition | Required purpose and invariants |
|---|---|
| Principals, credential digests, and sessions | Bind actors to merchants; support expiry/revocation; never persist raw access secrets |
| Immutable policy snapshots | Store the confirmation threshold, freshness window, memo-binding policy, and rules version selected for each new invoice |
| Evidence bundle metadata and encrypted payload | Bind receipt/raw-tx components, original hashes, source, submitter, and ciphertext to a single case |
| Append-only evaluation records | Preserve invoice/policy reference, verification/observation reference, evaluation time, owned allocation inputs, findings, balances, and final credit eligibility |
| Resolution evaluation reference | Tie each new decision to the exact evaluated state and source evidence, without rewriting the receipt result |
| Idempotency records | Unique principal/merchant + method + route/resource + key; store normalized request digest and resulting resource/outcome |
| Chain observation provenance | Bind an observation to network, txid, decoded raw-tx hash, source kind/ID, observation time, and relevant response data; retain all attempts |
| Event payloads | Store safe structured event content alongside the existing hashes and sequence; no secret evidence bytes in event payloads |
| Grants and consent records | Bind access/disclosure to the case and explicit evidence selections, with expiry/revocation and immutable consent history |

Preserve current rows. New references can initially be nullable for legacy records, but new service writes must provide them and legacy rows cannot become credit-eligible through guessed context. If adding uniqueness discovers duplicate invoice cases, fail the migration with a remediation report instead of deleting or merging records. Extend immutability protections to policies, evaluations, observations, and evidence metadata; credential/grant revocation and encrypted-content deletion are separate lifecycle operations.

Do not add invoice editing to P0. A merchant can close an uncredited case and create a new snapshot for corrected terms. A credited invoice cannot be replaced in a way that silently moves its allocations; that requires a later explicit correction/reversal design.

### Minimum workflow API

All successful workflow responses carry stable IDs and a report/schema version. Mutating workflow POSTs accept an `Idempotency-Key`; authorize first, then validate/replay it. Unknown request fields are rejected. Money is integer zatoshis; times are timezone-aware UTC; actor/merchant identity and chain trust are never client-controlled.

| Route | Minimum input | Result / authority |
|---|---|---|
| `POST /api/invoices` | Expected integer amount, network/pool, receiver address, memo text or null, expiry or null | Immutable snapshot plus server-selected policy; merchant only |
| `POST /api/cases` | Invoice ID | Case ID/state/version; merchant only |
| `GET /api/cases` | Cursor and optional state filter | Merchant-owned case summaries; add this read route for the dashboard |
| `GET /api/cases/{id}` | Case ID | Existing merchant case detail; preserve this contract and deny ungranted roles |
| `GET /api/cases/{id}/report` | Case ID and optional verification ID | Existing merchant report; add explicit reviewer projection in M4.5 |
| `POST /api/cases/{id}/claims` | Optional reported txid and note | Assertion record; merchant or scoped customer |
| `POST /api/cases/{id}/evidence` | Optional receipt/raw-tx strings, optional claim ID, source label, consent acknowledgement | Evidence bundle ID; merchant or scoped customer; source label is not a trust grant |
| `GET /api/cases/{id}/evidence/{evidence_id}` | Case and evidence IDs | Existing merchant metadata read; add permitted reviewer projection in M4.5 |
| `GET /api/cases/{id}/evidence/{evidence_id}/content` | Case and evidence IDs | M4.5 scoped original components; selected evidence and consent required for reviewers; never ciphertext or key material |
| `POST /api/cases/{id}/verify` | Evidence bundle ID | Persisted result, observation, evaluation, and updated case version; merchant only in P0 |
| `POST /api/cases/{id}/resolve` | Action, verification ID where required, expected case version, reason | Resolution/allocated output reference and post-decision balances; merchant only |
| `POST /api/cases/{id}/chain-observations` | Verification ID | Existing merchant refresh with provenance; includes closed cases and does not allocate credit |
| `POST /api/cases/{id}/grants` | Customer/reviewer role, expiry, allowed report/evidence selections, export permission | One-time access code plus grant metadata; merchant only |
| `GET /api/cases/{id}/grants` | Case ID | Owned grant metadata for management, never reusable access codes |
| `DELETE /api/cases/{id}/grants/{grant_id}` | Grant ID | Revocation; merchant only; already-revoked is harmless |
| `GET /api/cases/{id}/export` | Case ID | Complete or explicitly scoped/limited `CasePacketV1`; authorization rechecked |
| `POST /api/session`, `DELETE /api/session`, `GET /api/session` | Initial access code for creation | Browser session creation, logout, and current access scope |

Creation normally returns 201; reads and recorded-action replay return 200. Use 401 for missing/invalid credentials, 403 for a forbidden action on an otherwise accessible case, 404 for inaccessible objects, 409 for stale versions/idempotency mismatch/allocation conflict or ineligible business actions, 413 for limits, 422 for input validation, and 429 for verifier capacity. A completed verification attempt with an unsuccessful receipt state returns its domain result, not a misleading server failure.

Keep `CaseReportV1` separate from the existing receipt result. Include `case`, `invoice`, `policy`, `claims`, `evidence`, `verifications`, `chain_observations`, `evaluations`, `balances`, `resolutions`, `events`, and `disclosure_scope`, projected for the role. Approval input does not contain amount, receiver, output identity, approved-by identity, or trusted chain state; the service derives them from authorized stored records.

## 5. Approval transaction and state behavior

### Credit protocol

1. Authenticate/authorize the merchant and load the requested case/verification relationship. Check for an already completed idempotency result or same-invoice output allocation before external work; reauthorization always precedes replay.
2. For a genuinely new approval, refresh chain evidence outside the database transaction. Persist the immutable observation attempt. Failure leaves a useful diagnostic but cannot create a resolution or credit.
3. Begin a short transaction and claim the idempotency record. Use a unique insert/row lock so concurrent requests with the same key serialize. A different normalized body for that key returns 409. Exclude the idempotency header itself from the body digest.
4. Lock the immutable invoice row for allocation coordination, then the case row, always in that order. `SELECT FOR UPDATE` locks a row without modifying the invoice snapshot. All invoice-affecting writers follow this order. PostgreSQL documents the relevant [row-lock behavior](https://www.postgresql.org/docs/17/explicit-locking.html).
5. Recheck relationships and current authorization, then the semantic output allocation. If already allocated to this invoice, return the original allocation/resolution outcome without another decision event; this check precedes stale-version rejection for a completed retry. An allocation to another invoice produces an opaque conflict.
6. For a new allocation, compare the expected case version, require a nonterminal case, and check that the fresh observation still meets its age bound. Load all approved allocations for this invoice and the candidate output's global allocation status. The global lookup is internal and must not reveal foreign case details.
7. Re-evaluate the immutable invoice/policy, verification, observation, and current approved allocations. Block invalid/unsupported/unavailable evidence, missing reference binding, recipient mismatch, insufficient/stale confirmation, conflict, or projected overpayment. Derive the allocation amount from the recovered output only.
8. Write the decision evaluation, merchant resolution, full-output allocation, case state/version update, event with chained hash, and successful idempotency result in the same transaction.
9. Commit once. On allocation uniqueness failure, roll back the entire decision transaction, reread the winning allocation in a fresh transaction, and return same-invoice replay or cross-invoice conflict. Do not leave a resolution behind from the losing attempt.

Different outputs on one invoice serialize through the invoice lock, so each decision sees the latest approved balance. Competing invoices for one output are protected by the allocation primary key. A crash before commit leaves no business side effects; a lost response after commit is recovered by the same key or semantic output lookup.

Limit database lock waits to five seconds and return a retryable conflict without partial writes when exceeded. Idempotency records contain safe resource/outcome references, not raw evidence or credentials, and are retained for the life of the case. Replay reconstructs the original safe outcome after current authorization checks. Non-credit decisions also require idempotency but never create allocations.

### States and audit events

- New case → `OPEN`; missing required evidence or a merchant request → `AWAITING_EVIDENCE`; a persisted usable attempt or evidence rejection awaiting another attempt → `UNDER_REVIEW`.
- An approved partial payment leaves `UNDER_REVIEW`. A fully covered invoice after explicit approval can close that case as `RESOLVED`. `CLOSE_UNRESOLVED` writes `CLOSED_UNRESOLVED` without credit.
- Terminal cases reject new mutations except semantic/idempotent retries of completed actions. Invoice balance remains separately visible; terminal status does not override arithmetic.
- Increment `Case.version` for accepted workflow mutations and append a monotonically sequenced case event under the case lock. Store action, actor, UTC time, safe payload, its hash, previous event hash, and the event hash. Hash the serialized payload separately; hash the event's case ID, sequence, actor, action, time, payload hash, and previous hash using the same versioned serialization profile. The first previous hash is null; never include an event's own hash in its hash input.
- A stale decision returns the latest version and a safe refresh instruction, not an automatic retried approval. The merchant must review changed balances/evidence.
- Reports never overwrite historical approval context with newer observation results. Current warnings and historical decisions can coexist.

## 6. Test plan and traceability

Use real PostgreSQL for transactions/locks and the real Rust binary for cryptographic cases. Mock only the external chain observer when a scenario requires deterministic confirmation; identify those tests as simulated-source tests. SQLite and mocked database inserts cannot demonstrate the allocation guarantees.

| Test group | Required assertions | PRD scenarios |
|---|---|---|
| First vertical slice | Offline blocks approval; simulated-source harness approves only on merchant action; balances and report are correct | A-01, A-03, A-10 |
| Aggregate payments | Two approved synthetic outputs of 600,000 and 400,000 cover 1,000,000; label these rule/service inputs synthetic, not additional historical crypto fixtures | A-04 |
| Retry after response loss | Same key/body replays; changed body conflicts; different key/same allocated output adds no resolution, event, or credit | A-05 |
| Concurrent approval | Same output/same invoice commits once; same output/two invoices has one winner; different outputs/one invoice recheck the total and cannot bypass overpayment review | A-06 |
| Output identity | Distinct outputs in one tx are independent; changing pool/network/index cannot bypass binding or allocation identity | A-02, A-07 |
| Failure/rollback | Tamper, wrong txid, bad index, missing input, unsupported format, timeout, malformed raw tx, and injected write failures produce no partial credit | A-02, A-08, A-14 |
| Binding and policy | Normalize equivalent receiver encodings; reject mismatched pool/network, missing reference binding, unsafe candidate amount, insufficient confirmations, and stale observation | A-09, A-10 |
| Chain trust | Ignore forged request fields; verify raw bytes/network; preserve unavailable/not-found/side-chain distinctions; refresh failure cannot reuse stale success | A-08, A-10 |
| Access and consent | Two merchants plus all grant scopes; revoked/expired sessions, unconsented evidence, arbitrary IDs, export/download restrictions | A-11, A-12 |
| Export/replay | Original bytes and policy/rules context survive; tampering fails integrity; historical math reproduces; foreign conflicts remain scoped; concurrent export is internally consistent | A-13 |
| History and migration | No invoice edits or partial decision rows; event chain is reproducible; migrate existing records without inventing policy; readiness tracks head | A-14 |
| Operational/browser | Request/process limits, secret redaction, safe memo rendering, complete user flows, restart/retry, encrypted restore, and clean deployment | A-15 and P0-07 |

Run the existing verifier/rules/API suites after integration changes and `make test-db` for every schema/allocation change. Add targeted service/API tests under the existing test tree and browser tests in the frontend package. Generate OpenAPI types and check them for drift; regenerate the existing verifier schema only if its actual model changes.

Recorded M1/M2 and M3 adapter results are in [DEVELOPMENT.md](DEVELOPMENT.md), including the latest 12 Rust, 175 Python, and 151 PostgreSQL passing tests. These are historical results, not checks rerun by this assignment update. Cargo, uv, and a disposable PostgreSQL database must be available before recording new implementation results. Do not count source inspection, test presence, or a skipped database suite as a passed acceptance gate.

## 7. Release evidence, dependencies, and immediate next task

### Evidence to retain

Use the [release evidence index](release-evidence.md) for A-01–A-15 run references, retained sanitized recovery results, repeatable offline demo commands and remaining owner handoffs.

- An acceptance checklist with each A-ID, command/scenario, actual outcome, commit/revision, environment, and timestamp.
- A first-slice trace identifying invoice, case, evidence, verification, observation, evaluation, resolution, and allocation IDs; simulated and live traces remain distinct.
- Concurrency/rollback results, scoped-access results, and a sample authorized packet plus replay output.
- Tested RPC node/version and sanitized live chain observation for the historical output; no credentials in the evidence bundle.
- Deployment/restart/restore rehearsal, screenshots, known limitations, the PRD's video artifacts, and actual discovery notes.

### External dependencies and boundaries

- **Live RPC:** the operator-selected QuickNode public demo endpoint passed the [M3.1 acceptance run](chain.md#recorded-live-run). Evidence merged in PR #27; final release association remains required. A deployment must explicitly configure its trusted source; an unavailable lookup continues to block new credit.
- **Credentials and encryption:** provision access credentials and the evidence key through local operator tooling and deployment secrets. Never place them in the repository or shared reports.
- **Private-data retention:** before a real customer pilot, specify retention/deletion for original bundles, derived verification fields, invoice/claim/decision data, and backups together. Implement an authorized purge process consistent with the append-only application's limits. Expiring only the original blob while retaining all recovered personal fields is insufficient. This gate does not prevent a public-fixture hackathon demo.
- **P1 exclusions:** no CipherPay adapter, notifications, refund execution, signed report, browser WASM, CSV, or new-chain/transaction-format work on this path.

**Immediate tasks:** M4.0–M4.5 and M5.0–M5.2 are merged. Person 3’s export/replay recovery merged in PR #24. The release-evidence consolidation is present in main. The M3.1 live fixture observation and merchant approval trace merged in PR #27. The [remaining handoffs](release-evidence.md#remaining-handoffs-and-release-decision) identify operator/team artifacts for full release. Person 4's M6 implementation and browser evidence are recorded in [frontend.md](frontend.md); PR #26 is published and awaits review/CI/merge. Check active branches/PRs again when claiming any task; this document does not reserve remote work by itself.

### Sources checked for the proposed approach

- [PRD](PRD.md), [Preflight](../instructions/Preflight.md), [teammate guide](../TEAM_GUIDE.md), and [security boundaries](security.md).
- [Existing database tests](../apps/api/tests/test_postgres.py), [rules tests](../apps/api/tests/test_rules.py), [verifier tests](../apps/api/tests/test_verifier.py), and [API tests](../apps/api/tests/test_api.py).
- [PostgreSQL 17 explicit locking](https://www.postgresql.org/docs/17/explicit-locking.html).
- [Cryptography AES-GCM API](https://cryptography.io/en/stable/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM).
- Zebra's [RPC methods](https://zebra.zfnd.org/internal/zebra_rpc/methods/index.html), [transaction object](https://zebra.zfnd.org/internal/zebra_rpc/client/struct.TransactionObject.html), [block header](https://zebra.zfnd.org/internal/zebra_rpc/methods/struct.BlockHeaderObject.html), and [chain info](https://zebra.zfnd.org/internal/zebra_rpc/methods/struct.GetBlockchainInfoResponse.html). Their pages may show different generated crate versions; the configured node's actual API must pass M3's compatibility test.
