# M7.2 release evidence index

Person 3 maintains this index. Baseline: `f2436a92e9c2f6068454e19f8f99732129223e6a`,
the merge of [PR #24](https://github.com/Kurisu-Labs/zecsolve/pull/24) on October 12,
2026. M4.0–M4.5, M5.0–M5.2, backend deployment preparation, and backend recovery
with scoped export/replay are merged. **Full release remains incomplete:** M3.1
needs a trusted RPC endpoint and live approval trace; Person 4 owns unfinished
M6/browser acceptance; operator and team artifacts below remain outstanding.

This index consolidates existing runs. It does not turn source inspection,
simulated observations, frontend unit tests, or a documentation PR into a release
pass. [DEVELOPMENT.md](DEVELOPMENT.md) remains the historical log; the
[assignment board](IMPLEMENTATION_PLAN.md#feature-board) remains the ownership
source. The [PRD acceptance rows](PRD.md#131-acceptance-scenarios--required-outcomes-not-reported-passes)
define the required behavior.

## Evidence register

CI records E-01–E-03 target implementation revision
`4c47e4bf9f3c603c9ae6853c82de1fb0f207d8da`, included in PR #24. Their runtime and
test sources match the baseline above; the subsequent branch commit changes
documentation only. Times are UTC. GitHub job status and artifact provenance were
rechecked during this consolidation; these are the original executions.

| ID | Command and actual outcome | Time, environment and source |
|---|---|---|
| E-01 | `make lint`, `make test`, `make test-db`, `make poc`: passed; 12 Rust, 275 non-database Python and 236 PostgreSQL tests; offline fixture recovery/tamper rejection | [Foundation job](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38218166014/job/114707697759), 2026-10-12 07:30:55–07:33:58; Ubuntu runner, Python 3.14, Rust 1.99.0, PostgreSQL 17. Counts recorded in [Item 20](DEVELOPMENT.md#item-20--m72-exportreplay-recovery-integration); setup in [CI](../.github/workflows/ci.yml). |
| E-02 | `python scripts/check_deployment.py --recovery`: all 24 container groups passed; four recovery/export checkpoints; no live confirmation | [Container job](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38218166043/job/114707697872), 2026-10-12 07:30:55–07:34:38; report time 07:34:34.032559; Linux 6.17.0-1022-azure x86_64, Python 3.14.8, Docker 28.0.4, PostgreSQL 17, packaged real verifier. [Retained report](evidence/m7-recovery-4c47e4b.json). |
| E-03 | `npm ci --ignore-scripts --no-audit --no-fund`, `npm test`, `npm run build`: passed for the existing frontend | [Web job](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38218166014/job/114707697512), 2026-10-12 07:30:55–07:31:16; Ubuntu runner, Node 24. This is unit/build evidence; actual-browser acceptance remains open. |
| E-04 | Installed offline replay examples: valid `0/REPRODUCED`, tampered `1/FAILED`, scoped and missing-version `2/LIMITED`, unsupported-version `3/UNSUPPORTED` | Exact file hashes and CLI output in [replay-results.json](../fixtures/packets/replay-results.json). Reproduced byte-for-byte locally by 2026-10-12 12:09:30Z, macOS 27.0.1 arm64, Python 3.12.14, Rust 1.99.0, baseline `f2436a9` plus documentation-only changes; [Item 21](DEVELOPMENT.md#item-21--m72-release-evidence-consolidation). E-01 also runs CLI/engine regressions; E-02 runs downloaded authorized exports. |

E-02's retained JSON is the byte-for-byte `recovery-result.json` member of
GitHub artifact **11732947385**, named `backend-recovery-evidence`, from run
**38218166043**. The downloaded ZIP matched GitHub's SHA-256
`16a261c0d136aed6de09b4b4f3bbcddd158ae1f6365bd353b59eeed7984505bf`.
The retained JSON SHA-256 is
`6466446d3ff7c67976695fcc66e201e6a17923745e67ed61a3a4b363ea6a6ce9`.
Retaining the JSON keeps the evidence available after the CI artifact expires.
It contains synthetic row counts, hashes and check outcomes, without packet
bodies, credentials, keys or customer evidence. It explicitly retains
`working_tree_changes=false`, `live_confirmation=false` and
`release_complete=false`. Its checksum establishes file identity, not independent
attestation of the test runner.

The macOS timeout failures and working-tree runs in Item 20 remain historical
limitations. They are not relabeled as passing or clean runs. E-01 supplies the
complete successful Linux suite.

## A-01–A-15 traceability

Every row below has recorded backend evidence, with E-01 identifying the full
unit/database execution and E-02 identifying runtime checks. Named tests are
entry points within those runs, not newly claimed individual executions. To
repeat one, use `uv run --locked pytest path/to/test_file.py::test_name`; database
tests also require `ZECSOLVE_TEST_DATABASE_URL` for a disposable PostgreSQL
database. Preserve the full-suite command/result when using E-01 as evidence.

| ID | Demonstrated backend outcome and exact scenario | Evidence | Outstanding acceptance / owner |
|---|---|---|---|
| A-01 | Public Orchard fixture recovers 100,000 zatoshis; offline state remains unavailable. [test_verifier.py](../apps/api/tests/test_verifier.py): `test_mainnet_fixture_recovers_expected_fields`; E-02 public-fixture check. | E-01, E-02 | P3: include the trace for the final release revision; live inclusion is separately M3.1. |
| A-02 | Tampered OCK has no recovered output; txid/output-index failures stay distinct. [test_verifier.py](../apps/api/tests/test_verifier.py): `test_tampered_ock_is_invalid_without_recovered_fields`, `test_distinct_failure_reasons`; [demo test](../apps/api/tests/test_resolution_demo.py): `test_isolated_demo_uses_real_recovery_and_labels_simulated_credit` checks tampered approval denial. | E-01 | P4: negative-evidence browser presentation and absence of credit. |
| A-03 | Unapproved 100,000 on a synthetic 200,000 invoice gives 0 credited, 200,000 outstanding, 100,000 candidate/projected outstanding. [test_rules.py](../apps/api/tests/test_rules.py): `test_unapproved_recovery_is_only_a_projection`; [test_verification_api.py](../apps/api/tests/test_verification_api.py): `test_authenticated_invoice_to_evidence_verification_and_report`. | E-01 | P4: first workflow against the actual backend. |
| A-04 | Synthetic 600,000 + 400,000 approvals cover 1,000,000. [test_resolution_safety.py](../apps/api/tests/test_resolution_safety.py): `test_two_synthetic_outputs_accumulate_to_full_balance`. These are synthetic accounting inputs. | E-01 | Backend scenario demonstrated; P3 retains its reference in the final revision's evidence. |
| A-05 | Same-output/key retries preserve the original decision and add no credit; recovery preserves accepted retries. [test_resolutions.py](../apps/api/tests/test_resolutions.py): `test_simulated_partial_approval_and_semantic_replay_are_atomic`; E-02 crash/database/restore retry groups. | E-01, E-02 | P4: lost-response/retry browser flow. |
| A-06 | One winner for competing invoices; same-invoice concurrency commits once; conflict is opaque. [test_resolution_safety.py](../apps/api/tests/test_resolution_safety.py): `test_concurrent_two_invoices_one_output_has_one_winner_and_opaque_conflict`, `test_concurrent_same_output_same_invoice_commits_once`. | E-01; E-02 restored uniqueness | P4: conflict flow; P3: final demo trace. |
| A-07 | Distinct output identities in one transaction allocate independently using synthetic rows. [test_postgres.py](../apps/api/tests/test_postgres.py): `test_two_outputs_in_one_transaction_can_be_allocated`. | E-01 | Backend scenario demonstrated; P3 retains its reference in the final revision's evidence. |
| A-08 | Missing, unsupported, unavailable and execution-error outcomes remain distinct from invalid evidence. [test_verifier.py](../apps/api/tests/test_verifier.py): `test_missing_evidence_and_missing_binary_are_not_invalid`, `test_unknown_consensus_branch_is_unsupported`, `test_invalid_transaction_data_does_not_accuse_receipt`, `test_subprocess_is_bounded`; [test_persisted_verification.py](../apps/api/tests/test_persisted_verification.py): `test_unsuccessful_attempts_are_persisted_honestly`. | E-01 | P4: status/error displays; P3: actual-source behavior in M3.1. |
| A-09 | Receiver/reference mismatch blocks eligibility; overpayment requires review. [test_rules.py](../apps/api/tests/test_rules.py): `test_recipient_and_memo_mismatch_block_matching`, `test_missing_reference_requires_review_without_unique_receiver`, `test_overpayment_requires_review`; [test_decision_rules.py](../apps/api/tests/test_decision_rules.py): `test_approval_gates_preserve_memo_overpayment_and_allocation_rules`. | E-01 | P4: policy/balance presentation. |
| A-10 | Offline approval is denied and request fields cannot invent chain trust. [test_resolutions.py](../apps/api/tests/test_resolutions.py): `test_offline_approval_is_blocked_without_partial_decision`; [test_verification_api.py](../apps/api/tests/test_verification_api.py): `test_verification_and_report_require_ownership_and_reject_chain_spoofing`. RPC tests use synthetic responses. | E-01, E-02 | Operator supplies endpoint; P3 records actual node/version, fixture observation and normal merchant approval in M3.1. |
| A-11 | Merchant isolation and customer/reviewer read/write/export scopes enforced. [test_resolution_safety.py](../apps/api/tests/test_resolution_safety.py): `test_foreign_merchant_and_wrong_case_cannot_decide`; [test_reviewer_reports.py](../apps/api/tests/test_reviewer_reports.py): `test_route_role_matrix_and_exact_component_response`; [test_exports.py](../apps/api/tests/test_exports.py): `test_export_http_permission_matrix_and_download_contract`. | E-01, E-02 scoped HTTPS checkpoints | P4: all-role browser acceptance. |
| A-12 | Expiry/revocation and evidence consent enforced, including after restore. [test_grants.py](../apps/api/tests/test_grants.py): `test_grant_authentication_checks_expiry_revocation_and_role`, `test_reviewer_selection_requires_actual_sharing_consent`; [test_exports.py](../apps/api/tests/test_exports.py): `test_revocation_during_export_decryption_prevents_disclosure`. | E-01, E-02 restored customer/reviewer revocation | P4: disclosure/access screens explain that downloaded copies remain usable. |
| A-13 | Authorized packets preserve exact components and historical context; scoped exports remain limited; concurrent export stays consistent; tampering fails. [test_exports.py](../apps/api/tests/test_exports.py): `test_merchant_export_replays_current_claim_consent_and_exact_evidence`, `test_export_snapshot_does_not_mix_concurrent_approval`; [test_replay.py](../apps/api/tests/test_replay.py): `test_real_recovery_and_both_historical_rules_reproduce_without_network`. | E-01, E-02 all four export/replay checkpoints, E-04 | P4: authorized download UI; P3: final revision's export/replay trace. |
| A-14 | Failed decisions leave no business rows; stale concurrent review is rejected; invoice/event history stays immutable. [test_resolution_safety.py](../apps/api/tests/test_resolution_safety.py): `test_failed_decision_rolls_back_all_business_records_but_keeps_refresh`, `test_different_outputs_serialize_and_require_fresh_review_before_overpayment`; [test_postgres.py](../apps/api/tests/test_postgres.py): `test_snapshots_and_events_reject_edits`. | E-01, E-02 migration/restore invariants | P3: final evidence reference; P4: stale-version flow. Correction/version-linkage workflow remains outside P0. |
| A-15 | Actual TLS, request/process limits, disabled public POC/docs, readiness recovery and secret-canary log checks pass; restart/restore/export can be repeated. [Deployment procedure](deployment.md), [recovery checks and limits](recovery.md#what-is-exercised), [harness](../scripts/check_deployment.py). | E-01 deployment regressions, E-02 | P4: safe rendering/browser evidence; operator: deployment controls below; P3/team: final demo and release artifacts. |

## Repeatable demonstrations without RPC

Run from the repository root. Install the [README prerequisites](../README.md#run-the-proof-of-concept)
and run `make setup` first; initial dependency installation can use the network.
Use public fixtures and disposable test data. Keep historical evidence files
unchanged unless deliberately recording a new, separately attributed run.

### 1. Historical recovery, candidate balance and invalid evidence

```sh
make poc
```

Expected: `VALID` recovery of 100,000 zatoshis, tampered receipt `INVALID`,
`chain_state=UNAVAILABLE`, 0 credited, 200,000 outstanding, 100,000 candidate and
100,000 projected outstanding. The [POC](../scripts/poc.py) writes no allocation.
The public receipt/transaction's source, pinned revision, hashes and MIT license
are in the [fixture manifest](../fixtures/manifest.json).

### 2. Simulated approval, retry and cross-invoice conflict

Set `ZECSOLVE_TEST_DATABASE_URL` privately to a disposable PostgreSQL database
whose role may create/drop schemas, as in the [isolated demo guide](resolutions.md#isolated-first-slice-demo).
Then run:

```sh
uv run --locked python scripts/demo_resolution.py
```

Expected: `source_kind=SIMULATED`, `live_confirmation=false`, offline approval
denied, 100,000 credited/100,000 outstanding after simulated approval, the same
resolution on retry, a second-invoice conflict, and invalid tampered evidence
without credit. The output contains safe invoice/case/verification/observation/
evaluation/resolution/output references and schema cleanup status. This exercises
the real application services in a temporary schema; it is not a browser or live
payment demonstration. Never enable simulated confirmation in deployment.

### 3. Complete/scoped packets and replay limits

```sh
uv run --locked replay-case fixtures/packets/complete-v1.json --verifier target/debug/zecsolve-verifier
uv run --locked replay-case fixtures/packets/complete-v2.json --verifier target/debug/zecsolve-verifier
uv run --locked replay-case fixtures/packets/scoped.json --verifier target/debug/zecsolve-verifier
```

Run each command separately: complete fixtures exit 0/`REPRODUCED`; the scoped
fixture deliberately exits 2/`LIMITED`. These [checked-in samples](../fixtures/packets/README.md)
combine a real public receipt with synthetic invoices, consent and approval
history. They are not downloaded merchant exports. Hashes do not authenticate
authors, and offline replay does not prove fresh chain inclusion.

For the five valid/tampered/scoped/version examples, run
`uv run --locked python scripts/record_replay_examples.py`. It regenerates
[replay-results.json](../fixtures/packets/replay-results.json) using temporary
variants; compare with `git diff --exit-code -- fixtures/packets/replay-results.json`.
Expected CLI statuses are in E-04. The script records results rather than
asserting the expected statuses, so inspect them before calling the run passed.

For **actual authorized HTTP exports** through the deployed backend, use Docker
with Compose and OpenSSL, then run:

```sh
uv run --locked python scripts/check_deployment.py --recovery
```

The [recovery harness](recovery.md) creates its own disposable TLS deployment and
uses real grants/sessions. At `before_restart`, `after_api_restart`,
`after_database_restart` and `after_encrypted_restore`, merchant exports must
return 0/`REPRODUCED`, selected-reviewer and case-only exports 2/`LIMITED`, and
tampered packets 1/`FAILED`. History hashes must stay equal per role after removing
only `report.generated_at`. Export is denied for anonymous, customer, revoked and
report-only access. Packet bodies remain temporary; retain only the sanitized
`.cache/recovery-result.json`. Replay runs with Docker networking disabled.
HTTP cookie clients in this harness do not replace Person 4's browser tests.

## Remaining handoffs and release decision

| Gate / owner | Evidence required to close it | Current state |
|---|---|---|
| M3.1 / operator + P3 | Operator supplies a compatible trusted endpoint privately. P3 records node/version/method compatibility, bound fixture/network/block/confirmation facts, freshness and the ordinary merchant approval trace, with revision/time/environment and sanitized IDs. Follow [chain.md](chain.md#pending-live-gate). | Externally blocked: endpoint unconfigured; no live pass. |
| M6 and full M7.1 / P4, then P3 | P4 provides actual-backend merchant/customer/reviewer browser results, retry/conflict/session/negative paths, authorized export download, keyboard/responsive checks and screenshots. P3 associates them with the same-origin deployed revision and integrates deployment/CI changes if required. | Initial frontend partial; remaining M6 integration/acceptance retains its explicit-resumption gate. E-03 does not close it. |
| Operator deployment / operator + P3 | Record the actual target/image revision, TLS and access provisioning, volume encryption, external evidence/backup key custody, backup/recovery point and restore procedure. Confirm the recovery limitations and reconcile revocations newer than any restored backup. | Disposable-container evidence exists; target-specific operator confirmation outstanding. No production backup, PITR or recovery-time guarantee is claimed. |
| Final acceptance/demo / P3 + team | Collect the final revision's test/CI results, all scenario outcomes, live trace, authorized packet/replay evidence, P4 screenshots and a repeatable demo with known limitations and attribution. Identify every public, synthetic, simulated and live input. | Evidence index and offline procedures available; assembled final release bundle incomplete. |
| Discovery and submission / team lead + team; P3 indexes supplied artifacts | Two actual merchant/payment-provider discovery notes including negative feedback/evidence availability; English presentation/demo artifacts and team-managed registration/submission confirmation per PRD. | Team-supplied artifacts not yet recorded here. No outreach or submission is implied by this task. |
| Private-customer pilot / operator + team | Document retention/deletion across originals, derived fields, claims/decisions and backups, with an authorized purge process consistent with immutable history. | Separate prerequisite before private-customer use; not required to run the public-fixture demonstration. |

For each handoff, record: owner; acceptance IDs; exact commit/image; UTC execution
time; environment/tool versions; command or browser scenario; actual outcome;
input classification; sanitized artifact path/hash and CI/PR link; limitations.
Distinguish **passed**, **failed**, **blocked** and **not run**. Preserve previous
records instead of replacing their revisions or timestamps. Keep secrets,
credential-bearing endpoint URLs, dumps, private logs and customer packets out of
the repository; link only reviewed, appropriately shared evidence.

P3 closes full M7.2 only when the required acceptance gates pass and the assembled
evidence is reviewed and merged. A useful offline demo, all backend tests passing,
or this index's PR merging does not close the missing live/browser/team gates.
