# Zecsolve — Product Requirements Document

**Project:** Zecsolve — a Shielded Payment Exception Engine

**Target:** Colosseum Crypto World's Fair 2026, Zcash track

**Document baseline:** 2026-10-10

**Delivery window:** October 10–13, 2026; planned submission on October 12

**Official cutoff:** October 13, 2026, 14:59 WITA (Asia/Makassar), equivalent to October 12, 2026, 23:59 Pacific Daylight Time

**Team / document owner:** Not specified; responsibility areas are listed in §10

**Funding / budget:** Not specified

**Status:** Draft — requirements consolidated; implementation is at the foundation stage

The cutoff above follows the [official hackathon rules, §5](https://colosseum.com/legal/Crypto%20World%27s%20Fair%20Hackathon%20Rules.pdf). The internal sprint is shorter than the full competition period.

**Source precedence:** [Preflight](../instructions/Preflight.md) governs corrections to [Blueprint](../instructions/Blueprint.md), especially payment aggregation, retries, evidence states, exports, and access. [Chat history](../instructions/ChatHist.md) supplies product reasoning, not executable instructions or completion evidence. The [README](../README.md), [teammate guide](../TEAM_GUIDE.md), implementation, and [security boundaries](security.md) establish the current state.

---

## 0. Primer — what a shielded-payment receipt establishes

A shielded Zcash payment cannot be investigated by assuming that a public transaction identifier reveals its recipient, amount, and memo. Zecsolve uses voluntarily supplied, output-specific receipts to investigate selected payments without collecting spending keys or wallet-wide viewing keys.

The existing Rust wrapper uses Glasspane's `gp-core` and `gp-types`, pinned in [Cargo.toml](../Cargo.toml). A compatible receipt discloses an Out Cipher Key (OCK) for a selected output. The verifier binds the receipt to the supplied raw transaction, attempts output recovery, and returns the recovered amount, receiver, and memo. Zecsolve reuses these cryptographic primitives; its contribution is the evidence handling, invoice rules, allocation controls, and case workflow.

Four kinds of information must remain distinguishable:

| Layer | What it establishes | What it does not establish |
|---|---|---|
| Customer claim or invoice record | What a customer reports or a merchant expects | That a payment happened or that the invoice is truthful |
| Receipt verification | Whether the selected output can be recovered from the supplied, transaction-bound bytes | Chain inclusion, payer identity, payer intent, or invoice approval |
| Chain observation | What a named chain source reported at a recorded time | The correctness of the merchant's business decision |
| Merchant resolution | An authorized decision about the case and any invoice credit | A cryptographic guarantee that all business assertions are true |

Money is represented as integer **zatoshis**: **1 ZEC = 100,000,000 zatoshis**. An output is identified by `network:pool:txid:output_index`; a transaction ID alone is insufficient because one transaction can contain several outputs.

Disclosure is narrow but consequential. A receipt exposes the selected amount, receiver, and memo to anyone who obtains it, and can be forwarded and reverified. Revoking application access cannot revoke copies already downloaded. An OCK is intentionally disclosed output evidence, not a spending key or wallet-wide viewing key. These boundaries are documented in [security.md](security.md).

**Compatibility baseline:** the wrapper accepts mainnet receipt version 0 and version 5 transactions with NU5 through NU6.2 branches. The repository contains a real historical Orchard fixture and a tampered counterpart. The Sapling recovery path exists, but a historical end-to-end Sapling fixture is still missing. This PRD makes no Ironwood compatibility claim. The current offline verifier always reports `chain_state=UNAVAILABLE`.

## 1. Problem Statement

Merchants accepting shielded ZEC need a way to investigate payments that do not match an invoice without requesting access to a customer's entire wallet. A support conversation may combine an invoice, a customer's transaction claim, a processor observation, and a selectively disclosed receipt. Those inputs have different evidentiary strength.

Without a structured workflow, an operator can mistake an unverified claim for payment, compare one partial payment against an entire invoice, credit the same output twice, or share more information than a reviewer needs. The merchant also needs to explain why a case was resolved and preserve enough context to inspect that decision later.

Zecsolve's proposed product value is merchant case management with explicit evidence provenance, deterministic findings, output-level allocation protection, and a portable resolution record. The [original research](../instructions/Blueprint.md) treats this as a hypothesis. Demand for a standalone product, willingness to pay, and differentiation from gateway features remain unvalidated; this document makes no first-in-market or traction claim.

## 2. Goals

1. Let a merchant open a case from an immutable invoice snapshot, receive a customer claim and optional receipt, and understand what has and has not been verified.
2. Reproduce real historical Orchard output recovery and tamper rejection on the development and demo machines.
3. Explain three P0 scenarios: an invoice balance shortfall, an output already credited to another invoice, and invalid receipt evidence.
4. Prevent duplicate credit within one deployment, including retries and concurrent approvals, while aggregating all unique approved payments for an invoice.
5. Give merchants a reviewed resolution flow and reviewers explicitly authorized access to case evidence and a replayable JSON packet.
6. Deliver a reproducible hackathon demonstration with clear labels for historical fixtures, synthetic invoices, test data, live observations, and unfinished capabilities.
7. Conduct at least two merchant or payment-provider discovery conversations and record evidence for or against the product hypothesis.

## 3. Non-Goals — Hackathon MVP

- Creating a wallet, payment gateway, checkout system, escrow, or custody service.
- Collecting seed phrases, spending keys, or wallet-wide viewing keys.
- Sending, reversing, or automatically refunding ZEC. The application records decisions; it does not execute transfers.
- Automatically crediting an invoice solely because a receipt verifies.
- Generating Ironwood-native receipts or claiming compatibility with transaction formats that have not been implemented and tested.
- Proving payer identity, financial-statement completeness, or providing a regulation-grade audit opinion.
- Splitting one output across several invoices, detecting allocations in unrelated deployments, or providing a global double-claim registry.
- Production-scale operations, billing, accounting integrations, and a completed commercial SaaS offering.

## 4. Users & Personas

- **P1 — Merchant or payment-support operator.** Owns the invoice and case, reviews the evidence and outstanding balance, authorizes credit, and records a reason. This is the primary user.
- **P2 — Customer making a payment claim.** Supplies a transaction claim and, when available, an output-specific receipt through access limited to the intended case. Needs to understand what will be disclosed.
- **P3 — Reviewer.** Inspects the case report and only the evidence explicitly shared with them. Needs provenance, verification limits, and the merchant's reasoning without broader wallet or merchant access.
- **P4 — Payment-provider integrator.** May later supply authenticated invoice/payment observations. The integration must preserve the distinction between a provider statement and independently verified output data.

Hackathon reviewers are an additional demonstration audience. They must be able to distinguish the working foundation from the intended complete product.

## 5. User Stories

- As a merchant, I want to enter or import an invoice's expected amount, receiver, memo/reference, and expiry so the case is evaluated against a fixed record.
- As a merchant, I want to open a case and review its claims, evidence, findings, approved balance, and pending candidates together.
- As a customer, I want to submit a claim without a receipt when I do not have one, so missing evidence is represented honestly rather than treated as an invalid payment.
- As a customer, I want to understand the amount, receiver, and memo disclosure before sharing a receipt.
- As a merchant, I want multiple approved payments to add up correctly, so a fully covered invoice is not reported as underpaid because each individual payment is smaller than the invoice.
- As a merchant, I want a repeated submission for the same invoice to return the recorded allocation outcome without adding credit, while a conflicting claim against another invoice is blocked.
- As a merchant, I want the system to distinguish invalid evidence, unsupported formats, unavailable data, and execution failures so I can choose the next action.
- As a merchant, I want to approve or reject a proposed resolution with a reason, with approval, allocation, and audit history committed together.
- As a reviewer, I want to inspect authorized evidence and replay its verification from an exported packet without receiving wallet-wide keys.
- As an integrator, I want future provider observations to carry authenticated provenance and remain separate from receipt verification.

The intended journey is **invoice → case → claim/evidence → verification → review → resolution → export**. Every step after the stateless verification foundation requires application workflow work.

## 6. System Architecture

### 6.1 Current implementation and target boundary

The chosen architecture is a modular monolith: a planned Vue 3/TypeScript/Tailwind frontend, a FastAPI application, PostgreSQL, and a local Rust verifier invoked through a bounded adapter. Retain PostgreSQL for the case workflow; the existing constraints and migration already target it. The offline verification POC can run without a database.

| Area | Present in the repository at this baseline | Remaining for the target MVP |
|---|---|---|
| Verification | Pinned Glasspane integration, historical Orchard fixture, tampered fixture, versioned JSON result | Full workflow integration; historical Sapling fixture before claiming equivalent demonstrated coverage |
| API | Liveness, readiness, and token-protected stateless POC verification | Invoice, case, claim, evidence, persisted verification, resolution, and export services |
| Database | Models, initial migration, invoice immutability, append-only record triggers, output uniqueness | Transactional writers, access grants, idempotency handling, and snapshot version linkage |
| Rules | Approved-payment aggregation, candidate projection, recipient/reference checks, allocation conflict findings | Persisted policy context and integration with approvals and trusted observations |
| Access | One development POC bearer token | Merchant identity, case-scoped customer/reviewer permissions, and disclosure consent |
| Chain observations | Schema and explicit unavailable status | Trusted observation source, confirmation policy, and provenance collection |
| Frontend | Architecture choice only | Merchant dashboard, customer submission, and reviewer report |
| Export | Verifier result schema and fixture provenance manifest | Complete, authorized, replayable case packet |
| Delivery | Setup commands, tests, CI configuration, and development container configuration | Recorded release validation, deployment verification, demo, and evidence bundle |

This table reflects inspected source and documented behavior, not a fresh execution of acceptance tests. Database tests with synthetic rows do not establish that a complete merchant approval API exists. See the [teammate guide](../TEAM_GUIDE.md) for the implementation map.

### 6.2 Verification and evidence flow

1. Authenticate the caller and authorize access to the invoice/case before accepting or returning private evidence.
2. Store permitted evidence privately, preserving the submitted bytes, input hashes, source, and submission context. The current POC is stateless; this storage is planned.
3. Invoke the configured Rust executable with explicit arguments, isolated temporary files, size limits, and a timeout. User input must not select server paths, executable commands, or arbitrary fetch URLs.
4. Validate the returned result contract and input bindings. Interpret `receipt_state` and `reason_code`, not process exit zero alone.
5. Obtain any chain observation through a trusted application integration and record its source and observation time separately. Never accept a customer's claimed confirmation state as authoritative.
6. Evaluate normalized invoice terms against the recovered output, approved allocation history, and policy/observation context.
7. Present findings and candidate amounts for review. Verification and rule evaluation do not allocate credit.
8. On authorized approval, recheck current state and commit the resolution, allocation, and event atomically. Produce reports from those recorded facts.

The backend and pinned Rust binary share one Docker deployment. Frontend hosting on Vercel remains the blueprint's planned option. Public access and real customer evidence are gated on the scoped-access and private-storage requirements in §7; the current POC is a local development service.

### 6.3 Data and independent status contracts

Core records are merchants, immutable invoice snapshots, merchant-owned cases, claims, evidence, verification attempts, chain observations, approved output allocations, resolutions, and case events. The existing [database models](../apps/api/src/zecsolve/db/models.py) are the implementation baseline, not proof of completed service behavior.

| Dimension | Contract |
|---|---|
| Receipt state | `NONE`, `VALID`, `INVALID`, `UNSUPPORTED`, `UNAVAILABLE`, `ERROR` |
| Chain observation | `CONFIRMED`, `UNCONFIRMED`, `UNAVAILABLE`, with source and observation time |
| Case state | `OPEN`, `AWAITING_EVIDENCE`, `UNDER_REVIEW`, `RESOLVED`, `CLOSED_UNRESOLVED` |
| Rules | Multiple findings may coexist, such as `UNDERPAID` and `CHAIN_UNVERIFIED`; do not collapse them into one success/failure badge |
| Business resolution | An explicitly authorized decision, reason, actor, and timestamp; independent of receipt and chain states |
| Balances | Approved credit, outstanding balance, excess, candidate value, and projected outstanding balance remain separate |

Existing verifier results follow [the versioned JSON schema](../contracts/verifier-result.schema.json). Their `chain_state` is always `UNAVAILABLE`; future observations belong in the separate observation layer rather than overwriting the offline verifier's claim.

Invoices are immutable from creation in the current schema. A correction requires a new snapshot and re-review; version linkage remains a service design task. Output allocations contain approved credit only and use the full output identity as the database primary key. Append-only triggers protect ordinary application history, not against a database administrator; transactional event sequencing and hashing still need a writer.

### 6.4 Current and proposed API surfaces

**Existing endpoints:**

| Endpoint | Current behavior |
|---|---|
| `GET /health/live` | Process liveness only |
| `GET /health/ready` | Migration and executable checks; readiness failure returns 503 |
| `POST /api/poc/verify` | Bearer-token-protected receipt/raw-transaction content verification; no evidence persistence or allocation |
| `GET /docs` | Interactive API documentation |

**Proposed minimum workflow API — not implemented at this baseline:**

| Endpoint | Intended capability |
|---|---|
| `POST /api/invoices` | Create a merchant-owned immutable invoice snapshot |
| `POST /api/cases` | Open a case against an authorized invoice |
| `GET /api/cases/{id}` | Return the caller's authorized view of a case, findings, and balances |
| `POST /api/cases/{id}/claims` | Record a scoped customer or merchant claim |
| `POST /api/cases/{id}/evidence` | Accept permitted evidence with provenance and size limits |
| `POST /api/cases/{id}/verify` | Persist a verification attempt and evaluated findings |
| `POST /api/cases/{id}/resolve` | Record an authorized decision and, when eligible and approved, atomically allocate credit |
| `GET /api/cases/{id}/export` | Download an authorized case packet |
| `POST /api/integrations/cipherpay/webhook` | P1 only: authenticated, replay-protected provider observations |

Merchant and actor identity must come from authenticated application context, not arbitrary request fields. Request/response schemas for the proposed routes must be agreed before frontend integration. This PRD documents the intended interfaces; it does not add routes or modify the existing verifier contract.

### 6.5 Replayable JSON case packet

An authorized replayable export must contain enough information to repeat the relevant verification and rule evaluation:

- The immutable invoice snapshot, identifier, expected terms, snapshot hash, and applicable policy/version.
- The case and relevant claims, labeled as assertions rather than verified facts.
- The disclosed receipt and the actual raw transaction checked, with lossless representations, declared encodings, and input hashes.
- Evidence provenance and each relevant chain observation: source, state, observation time, and block/confirmation fields when available. Unavailable values must remain explicitly unavailable.
- Verifier identity/version, pinned Glasspane revision, result schema version, receipt outcome, reason codes, and recovered fields when verification succeeds.
- Rules version, evaluated inputs, findings, approved allocation context, candidate amounts, and balances as of the decision.
- The merchant's resolution, reason, approver, time, and relevant event history.
- A packet version and integrity manifest that states which bytes each hash covers, plus the limits of what can be replayed or independently established.

Preserve original evidence bytes. The verifier hashes decoded raw transaction bytes, while the fixture manifest hashes original files; these are different hash bases and must not be conflated.

Only authorized evidence may leave the application. If a view omits required evidence for privacy, label it as a limited report rather than a fully replayable packet. Cross-case allocation context must be scoped or redacted without disclosing another merchant's private case. **SHA-256 alone does not authenticate the report's author or establish the truth of an invoice or business decision.** Offline replay also cannot freshly establish chain inclusion from raw transaction bytes alone.

## 7. Requirements

### P0 — must ship for the complete hackathon MVP

| ID | Requirement | Acceptance boundary |
|---|---|---|
| P0-01 | Invoice and case workflow | Capture immutable invoice terms; bind every case to the correct merchant; record claims without treating them as verified truth |
| P0-02 | Real receipt verification | Reproduce historical Orchard recovery and tamper rejection; preserve transaction/output bindings and verifier provenance |
| P0-03 | Deterministic balances and findings | Aggregate approved payments; show candidate projections separately; explain underpayment, conflicting output allocation, and invalid evidence |
| P0-04 | Idempotent, atomic resolution | Merchant approval is required; same-invoice retries add no credit; cross-invoice concurrent claims cannot both win |
| P0-05 | Honest failure and proof states | Distinguish missing, invalid, unsupported, unavailable, and execution-error evidence; preserve independent chain and case states |
| P0-06 | Scoped access and private evidence | Enforce merchant ownership, customer submission grants, reviewer permissions, disclosure consent, and authorized export |
| P0-07 | Usable case views | Provide merchant review, customer submission, and reviewer reporting with visible evidence provenance, limitations, balances, and decision history |
| P0-08 | Replayable export | Deliver the complete packet specified in §6.5, subject to explicit disclosure permissions |
| P0-09 | Reproducible delivery evidence | Record acceptance results, setup/deployment checks, fixture attribution, screenshots, and an accurate demo |

The following rules make these commitments concrete.

#### 7.1 Payment aggregation and invoice binding

- Use integer zatoshis throughout storage and computation. Parse decimal ZEC input exactly, without binary floating-point currency arithmetic.
- `credited_zat` is the sum of **unique approved allocations** for the invoice. A recovered receipt is not approved credit.
- `outstanding_zat = max(expected_zat - credited_zat, 0)`; `excess_zat = max(credited_zat - expected_zat, 0)`.
- A matching, unallocated output can contribute to `candidate_zat`; `projected_outstanding_zat = max(expected_zat - credited_zat - candidate_zat, 0)`. A projection must not mark an invoice paid.
- An invoice for **0.01 ZEC (1,000,000 zatoshis)** with approved allocations of **0.006 ZEC (600,000)** and **0.004 ZEC (400,000)** has zero outstanding balance. Comparing either receipt independently with the entire invoice is incorrect.
- Compare normalized receiver bytes together with pool and network. Decode Unified Addresses before matching; different address strings can contain the relevant same receiver.
- Require an exact expected memo match or an explicitly established unique receiver binding. Amount equality alone does not bind an output to an invoice. Preserve memo mismatch findings and request review when reference binding is absent.
- Underpayment describes the approved invoice balance; it is not an accusation that a receipt is invalid. A partial matching output may be proposed for merchant approval when the other eligibility checks pass.

#### 7.2 Retry, conflict, and approval behavior

- Deduplicate by `network:pool:txid:output_index`, not transaction ID or uploaded-file hash alone.
- The same output against the same invoice is an idempotent retry. Return its recorded allocation outcome without adding credit or creating a second approval side effect.
- The same output against another invoice is `DUPLICATE_CLAIM`; block the second allocation. Do not expose the other invoice's private details to an unauthorized caller.
- Different outputs in one transaction may credit different invoices. Splitting a single output across invoices is outside P0.
- Recheck eligibility and allocation state inside the approval transaction. Approval, allocation, and the corresponding audit event must commit together or roll back together. Database uniqueness remains the final guard against concurrent requests.
- Receipt recovery and rule evaluation never allocate credit automatically. Current rule eligibility requires a trusted `CONFIRMED` observation; an unavailable chain source must not be silently promoted to confirmed or bypassed for the demo.
- A merchant may record a decision to seek more evidence or close a case unresolved without allocating credit. A resolved case must not imply a paid invoice unless its approved balance supports that conclusion.

#### 7.3 Evidence states and diagnostic language

| State | Meaning | Required treatment |
|---|---|---|
| `NONE` | No receipt was supplied | Request evidence; do not call the payment invalid |
| `VALID` | Supported receipt recovered the selected transaction-bound output | Show recovered fields and limits; keep chain and approval independent |
| `INVALID` | Receipt structure, binding, signature, or recovery check failed | Explain the failed check without accusing the customer of fraud |
| `UNSUPPORTED` | Format, network, branch, pool, or signature scheme is outside the implementation | Report the compatibility boundary; do not call the receipt tampered |
| `UNAVAILABLE` | Required input, source, or verifier is unavailable | Allow recovery/retry; preserve uncertainty |
| `ERROR` | Execution or processing failed, such as timeout or malformed raw transaction data | Report a technical failure; do not present it as evidence of tampering |

An external source returning “not found” does not by itself prove receipt manipulation. Distinguish an unavailable transaction lookup from an out-of-range output index in supplied, parsed, transaction-bound bytes. Preserve reason codes and provenance so these cases can be reviewed.

Chain observations are independently `CONFIRMED`, `UNCONFIRMED`, or `UNAVAILABLE`. A valid receipt and `CHAIN_UNVERIFIED` can coexist. The UI and export must preserve both facts.

#### 7.4 Access, disclosure, and operational limits

- Authenticate merchant actions and authorize every case read, write, evidence download, and export against its merchant ownership. A database foreign key is not authorization.
- Customer grants permit the intended claim/evidence submission only. Reviewer grants permit explicitly selected case information and evidence; they do not permit merchant approval or access to other cases.
- Explain and record consent for output-specific disclosure before sharing private evidence. Inform the discloser that downstream receipt copies remain forwardable after a grant is revoked.
- Store evidence privately with encryption and restricted access. Define retention, deletion, and consent handling before accepting real customer evidence. Until then, use only the already-public fixtures.
- Keep wallet keys and tokens out of logs and exports. Treat recovered memo content as untrusted data; do not render it as executable markup. Do not echo receipt contents in validation errors.
- Retain bounded verification: the current defaults are 16,384 receipt bytes, 4,000,002 transaction-hex bytes, a 4,200,000-byte API body limit, 32,768 subprocess-output bytes, a ten-second timeout, and two simultaneous verifier processes per API process.
- Preserve explicit subprocess arguments, private temporary files, cleanup, and secret isolation. Add deployment-level resource/rate controls before public exposure; current local defaults are not a production capacity claim.

See [security.md](security.md) for the existing controls and remaining deployment boundaries.

### P1 — desirable after the P0 workflow is complete

- Dedicated missing/wrong-memo, late-payment, and overpayment resolution workflows. P0 must still detect unsafe matching and flag overpayments for review; deferring the specialized workflow does not permit unsafe credit.
- An authenticated CipherPay observation adapter with signature validation, replay/idempotency handling, and verified field semantics.
- Notifications, CSV export, and signed merchant reports with accurately described guarantees.
- A historical Sapling fixture establishing end-to-end coverage for the existing recovery path.
- Browser-local WASM verification when compatible with the selected evidence and deployment model.

### P2 — future product work

- Tested support for newer transaction formats and Ironwood evidence, if required by prospective users.
- Richer provider/accounting integrations, collaboration, and team administration.
- Externally anchored history or stronger attestations where a concrete trust requirement justifies them.
- Explicit split allocations, production scaling, and validated pricing/billing.

These items must not delay or be implied by the hackathon MVP.

## 8. Success Metrics

### Leading — check before submission

- The three P0 scenarios produce reproducible, correctly differentiated results on the demo machine.
- Same-invoice retries add **zero** duplicate credit, and concurrent cross-invoice allocation tests produce **exactly one** successful allocation.
- The aggregation example in §7.1 produces a zero outstanding balance once both allocations are approved.
- A reviewer can distinguish customer assertions, recovered fields, chain observations, and the merchant decision, and replay the authorized evidence from the case packet.
- Setup and the documented demo can be reproduced from a clean environment, with limitations and required services stated.
- Every release acceptance result has an associated command/scenario, date, revision, and recorded outcome; no unexplained “complete” counter is used.
- At least **two** merchant/payment-provider discovery conversations are documented, including negative feedback and inability to obtain usable receipts.
- The demo, repository documentation, and evidence bundle consistently identify live, fixture-driven, synthetic, and unimplemented parts.

### Lagging — evaluate after the hackathon

Track actual exception volume, median time to resolution, the share requiring further evidence, the share lacking usable receipts, and incorrect/duplicate credit incidents. Establish baselines through real use before setting improvement percentages.

Commercial validation asks whether merchants experience the problem frequently enough to adopt a separate tool and whether payment providers prefer an integration. Subscription or per-case pricing remains a hypothesis, with no assumed revenue, customer count, or market size.

## 9. Phased Plan — October 10–13, 2026

All internal times below use **WITA (Asia/Makassar)**. The official cutoff is **October 13 at 14:59 WITA**; plan to submit on October 12. [Official timing](https://colosseum.com/legal/Crypto%20World%27s%20Fair%20Hackathon%20Rules.pdf)

| Date | Focus | Exit criterion / evidence |
|---|---|---|
| October 10 | Foundation: verifier, historical fixture, schema, pure rules, and bounded POC API | Reproducible valid/tampered runs; documented foundation boundaries. Source and tests exist; record execution results rather than inferring completion |
| October 11, first phase | One complete vertical slice: invoice → case → receipt → verification → matching → authorized allocation → reasoned report | Persisted workflow with correct balances, merchant scoping, and atomic approval; chain evidence or explicitly labeled test observations handled honestly |
| October 11, second phase | Retry/conflict/tamper paths, customer submission, merchant review, and reviewer view | End-to-end scenarios with access isolation and clear independent status displays |
| October 12, first phase | Replayable export, failure paths, deployment controls, and clean-environment rehearsal | Authorized export replay, recorded acceptance results, and a repeatable demonstration |
| October 12, second phase | Discovery conversations, screenshots, attribution, presentation/demo recording, and submission preparation | Honest validation notes and evidence for what was actually built |
| October 12, evening | Planned submission with buffer | Team handles registration/submission and verifies artifact access |
| October 13, before 14:59 | Contingency only | Check submission state and correct critical issues; do not reserve feature work for the deadline |

**Build order:** finish the narrow vertical slice before adding optional integrations. Then exercise same-invoice retry, cross-invoice conflict, concurrent approval, and tampered evidence against that flow.

**Fallback boundary:** if trusted confirmation access is unavailable, the historical receipt can still demonstrate output recovery and candidate balance projection with `chain_state=UNAVAILABLE`. Approval/conflict tests may use explicitly labeled synthetic observations or seeded allocations in an isolated demo/test environment. Such scenarios do not prove live confirmation or completion of the full live approval path. Preserve that limitation in the demo and submission evidence rather than weakening credit rules.

## 10. Team & Roles

Names, team composition, compensation, and document ownership have not been provided. The following responsibility areas are **unassigned**, not commitments made on behalf of particular people:

| Responsibility | Deliverables |
|---|---|
| Product / delivery owner | P0 decisions, acceptance tracking, discovery notes, document updates, and submission coordination |
| Backend workflow owner | Invoice/case services, persisted evidence and verification, versioned policy context |
| Resolution / access owner | Merchant identity, customer/reviewer grants, consent, atomic approvals, and idempotency |
| Verification / integration owner | Pinned verifier behavior, fixtures, compatibility limits, and trusted chain observations |
| Frontend owner | Merchant, customer, and reviewer flows; accurate balances and status presentation |
| Evidence / release owner | Export replay, validation records, deployment rehearsal, screenshots, videos, and attribution |

One person may cover multiple areas. Assign names before parallel implementation. Evidence capture and preservation of privacy boundaries are shared responsibilities.

## 11. Risks

| Risk | Mitigation / decision boundary |
|---|---|
| Deadline pressure hides incomplete workflow behind the verifier POC | Complete the vertical slice first; track foundation, target behavior, and recorded evidence separately |
| Needed payment formats exceed the pinned verifier's compatibility | State the tested range; use the historical Orchard fixture; do not claim Ironwood or equivalent Sapling coverage without tests |
| Customers/providers cannot supply usable output receipts | Permit claims without receipts; report insufficient evidence; validate evidence availability in discovery conversations |
| Chain observations are unavailable or untrustworthy | Preserve provenance and unavailable status; do not manufacture confirmation or bypass approval eligibility |
| Concurrent approvals or retried requests cause duplicate credit | Full output identity, transactional rechecks, database uniqueness, atomic history, and explicit race tests |
| Private evidence leaks across merchants or through reviewer sharing | Enforce case-scoped access and consent; minimize disclosures; explain irreversible forwarding of downloaded receipts |
| A hash or append-only database is described as an independent audit guarantee | State the integrity, operator, and authorship limits; preserve evidence for review without claiming business truth |
| A public demo exposes a development-only endpoint | Gate exposure on authorization, private storage, and deployment controls; use public fixtures while incomplete |
| Merchants prefer gateway-native features or exceptions are too rare | Collect negative as well as positive discovery findings; treat the standalone product and pricing as hypotheses |

## 12. Open Questions & Recorded Decisions

### Decisions established for this PRD

- Hackathon MVP is the delivery scope; longer-term features remain P1/P2.
- Preflight overrides conflicting Blueprint examples. In particular, approved payments aggregate, retries are not automatically conflicts, and unsupported/unavailable evidence is not invalid evidence.
- Retain the existing FastAPI/PostgreSQL/Rust foundation and planned Vue frontend.
- Use public historical Orchard fixtures for the reproducible verification baseline, with synthetic invoices explicitly identified.
- Credit is a merchant-approved database allocation, not a money transfer. Offline recovery does not establish chain inclusion.
- Source/test presence is not a release acceptance result. Preserve actual commands and outcomes when evidence is collected.

### Remaining questions

| Question | When it must be resolved | Current boundary |
|---|---|---|
| Who owns each work stream, the PRD, and submission? | Before assigning implementation work | Roles remain unassigned; no assumed team or budget |
| Can intended users obtain per-output receipts without exporting wallet-wide information? | During MVP discovery | Customer-provided selective evidence is the initial path; missing evidence remains acceptable input |
| Which trusted chain source and confirmation policy will govern approval, including stale observations? | Before the live credit-approval milestone | Offline recovery stays unavailable; synthetic test observations are labeled and isolated |
| Which provider fields are actually available and authenticated? | Before a P1 adapter is implemented | Do not infer amount, receiver, or confirmation semantics from a webhook event name |
| How will identities, reviewer/customer grants, consent records, evidence retention, and deletion be implemented? | Before private evidence or public case access | The POC token is insufficient; public fixtures only until this gate is satisfied |
| How are corrected invoice snapshots linked and existing cases re-reviewed? | Before invoice correction is exposed | Existing snapshots remain immutable; no in-place edits |
| What disclosure can a cross-case allocation conflict export include without exposing another merchant? | Before reviewer export ships | Require scoped context and explicit limitations; never expose unrelated private case data |
| Is newer/Ironwood payment evidence required by the first prospective users? | Before claiming suitability for their live payments | The current compatible historical-fixture POC does not establish that suitability |
| Will merchants adopt and pay for a separate case tool? | During and after discovery | Pricing, distribution, and market demand remain hypotheses |

These are product and implementation decisions still to be made, not reasons to mark requirements complete or silently reduce them.

## 13. Evidence & Hackathon Alignment

### 13.1 Acceptance scenarios — required outcomes, not reported passes

The coverage column identifies existing test sources or remaining work. **It is not a test execution log.** Record pass/fail outcomes, commands, revision, environment, and time separately when running release validation.

| ID | Scenario and required outcome | Coverage at this baseline |
|---|---|---|
| A-01 | Historical Orchard receipt recovers 100,000 zatoshis from the bound mainnet transaction; chain state remains unavailable offline | Existing verifier fixture tests |
| A-02 | Tampered OCK, transaction-ID mismatch, or invalid selected-output index is rejected without recovered credit or automatic invoice payment | Existing verifier negative tests; workflow assertion pending |
| A-03 | Synthetic 200,000-zatoshi invoice with the unapproved 100,000-zatoshi output shows 0 credited, 200,000 outstanding, 100,000 candidate, and 100,000 projected outstanding | Existing rules test and POC script |
| A-04 | Approved allocations of 600,000 and 400,000 satisfy a 1,000,000-zatoshi invoice | Existing pure rules test; persisted workflow test pending |
| A-05 | Reusing an output for the same invoice returns the prior allocation outcome and adds no credit or duplicate approval side effect | Existing rule test; API/idempotency test pending |
| A-06 | Reusing an allocated output for another invoice produces a conflict; simultaneous approvals produce exactly one allocation with consistent resolution/events | Existing rules and database race tests; atomic service test pending |
| A-07 | Two distinct outputs from one transaction may be allocated independently | Existing database test with synthetic rows |
| A-08 | Missing receipt is `NONE`; unsupported input is `UNSUPPORTED`; absent data/binary is `UNAVAILABLE`; timeout or malformed raw transaction is `ERROR`; none is presented as tampering | Existing verifier/adapter/rules tests; UI and future chain-source paths pending |
| A-09 | Receiver mismatch or absent invoice reference binding blocks eligibility; projected overpayment requires review | Existing rules tests; workflow presentation pending |
| A-10 | A valid receipt with unavailable confirmation cannot become confirmed through request input or receive automatic credit | Existing offline contract and rules coverage; trusted observation/approval integration pending |
| A-11 | Another merchant cannot read, modify, resolve, or export the case; customers and reviewers cannot exceed their grants | Full scoped authorization tests pending; current database ownership constraint is partial coverage only |
| A-12 | Grant revocation stops future application access; disclosures explain that previously downloaded receipts remain reusable | Grant/consent implementation and tests pending |
| A-13 | Authorized packet includes the §6.5 inputs, reproduces verification and historical rules, and identifies missing/redacted context without leaking other cases | Complete exporter and replay tests pending |
| A-14 | A failed or stale approval commits no partial allocation/resolution/event; invoice corrections cannot rewrite the original snapshot | Existing immutability tests; transaction/review/version-linkage tests pending |
| A-15 | Errors/logs/exports omit tokens and wallet-wide keys; limits constrain hostile inputs; deployment and demo are repeatable | Existing adapter/API tests and configurations; release/export/deployment validation pending |

Existing suites are [verifier tests](../apps/api/tests/test_verifier.py), [rules tests](../apps/api/tests/test_rules.py), [API tests](../apps/api/tests/test_api.py), and [PostgreSQL tests](../apps/api/tests/test_postgres.py). The documented commands are `make test`, `make lint`, and `make test-db` against a disposable PostgreSQL database. `make poc` exercises the offline demonstration. Future case, access, export, and UI tests must be added when those capabilities exist. No blanket “all acceptance tests complete” claim is supported by this document.

### 13.2 Demonstration narrative

1. **Underpayment / candidate projection:** show the synthetic **0.002 ZEC** invoice and real historical **0.001 ZEC** receipt. Before approval, display **0 credited**, **0.002 ZEC outstanding**, and **0.001 ZEC projected shortfall**. Explain that this is historical output recovery, not newly initiated checkout or live chain confirmation.
2. **Retry and conflict:** show the same output submitted to the same invoice without extra credit, then to a different invoice with a conflict. Identify whether the prior allocation came from a completed approval flow or an explicitly seeded demo scenario.
3. **Invalid evidence:** use the tampered receipt, show the verification reason, and demonstrate that rejection does not allocate credit or accuse the customer of fraud.
4. **Review and export:** inspect the recorded merchant decision and authorized packet, keeping recovered evidence, external observations, and business assertions visibly separate. Only demonstrate completed functionality as working.

### 13.3 Deliverables and evidence to collect

| Deliverable | Evidence |
|---|---|
| Verification foundation | Fixture manifest and hashes, pinned dependency/license attribution, valid and negative run outputs |
| Rules and resolution | Aggregation/retry/conflict results, concurrent approval results, and consistent allocation/resolution/event records |
| Access and interface | Merchant/customer/reviewer screenshots, access-isolation results, and disclosure explanation |
| Export | Authorized sample packet, replay instructions/results, and stated integrity/privacy limits |
| Release | Repository link, setup guide, deployment/run instructions, known limitations, revision and environment for validation |
| Product validation | At least two discovery notes, evidence availability findings, and candid demand/negative feedback |
| Hackathon artifacts | English presentation/demo materials, accessible repository/artifacts, and team-managed registration/submission confirmation |

The [official rules](https://colosseum.com/legal/Crypto%20World%27s%20Fair%20Hackathon%20Rules.pdf) assess functionality, impact, novelty, UX, open-source, and business plan; require English content; and require team members to register and the team lead to submit before the cutoff. The [hackathon FAQ](https://colosseum.com/hackathon) requests a two-to-three-minute presentation and a product demo of no more than three minutes.

The team must describe its own work and reused components accurately. Glasspane cryptography and the upstream public fixtures are reused; Zecsolve's adapters, workflow, rules, access controls, and case records must be described according to what actually ships. Product acceptance and market validation require their own recorded evidence.

---

## Sources

### Local requirements and implementation evidence

- [Preflight corrections](../instructions/Preflight.md) — authoritative aggregation, retry, failure-state, export, and access requirements.
- [Hackathon Blueprint](../instructions/Blueprint.md) — original scope, architecture, priorities, and delivery intent.
- [Product reasoning / chat history](../instructions/ChatHist.md) — historical context, interpreted through Preflight corrections.
- [README](../README.md) and [teammate guide](../TEAM_GUIDE.md) — current capabilities, setup, and remaining milestones.
- [Security boundaries](security.md) — existing controls and limitations.
- [Rules implementation](../apps/api/src/zecsolve/domain/rules.py), [status definitions](../apps/api/src/zecsolve/domain/statuses.py), and [database models](../apps/api/src/zecsolve/db/models.py) — current calculation, state, and persistence contracts.
- [POC API](../apps/api/src/zecsolve/main.py), [verifier adapter](../apps/api/src/zecsolve/adapters/verifier.py), and [Rust wrapper](../crates/zecsolve-verifier/src/main.rs) — implemented verification boundary.
- [Verifier result schema](../contracts/verifier-result.schema.json), [fixture manifest](../fixtures/manifest.json), and [POC script](../scripts/poc.py) — result contract, provenance, and synthetic-invoice demonstration.
- [Pinned Rust dependencies](../Cargo.toml) and [retained Glasspane MIT license](../third_party/glasspane/LICENSE) — dependency attribution.

### External sources — checked October 10, 2026

- [Crypto World's Fair event page](https://colosseum.com/worldsfair) — competition context and submission date.
- [Official hackathon rules](https://colosseum.com/legal/Crypto%20World%27s%20Fair%20Hackathon%20Rules.pdf) — authoritative timing, registration, judging, and content requirements.
- [Colosseum hackathon FAQ](https://colosseum.com/hackathon) — presentation/demo lengths and submission expectations; event-specific rules take precedence.
