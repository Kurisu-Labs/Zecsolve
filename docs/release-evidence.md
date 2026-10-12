# M7.2 release evidence index

Person 3 maintains this index. Current integration baseline:
`8e8843dce410aaed30e10d960af5de2c857e0edd`, the merge of
[PR #26](https://github.com/Kurisu-Labs/zecsolve/pull/26) on October 12, 2026.
M4/M5 and backend deployment/recovery/export are merged; PR #25's evidence
consolidation is in main. **M3.1 live evidence merged in PR #27 and P4's frontend
implementation/browser evidence merged in PR #26. Full release remains incomplete.**
P3’s browser CI and packaged deployment rehearsal passed on
`test/m7-browser-release-integration` (E-07–E-09); review/CI/merge of this slice and
the operator/team/final-bundle handoffs remain below.

This index preserves separately attributed historical, simulated, live and
browser runs. A result applies to its recorded revision and environment; it is
not a claim that every release gate passed on the current main.
[DEVELOPMENT.md](DEVELOPMENT.md) remains the historical log; the
[assignment board](IMPLEMENTATION_PLAN.md#feature-board) remains the ownership
source. The [PRD acceptance rows](PRD.md#131-acceptance-scenarios--required-outcomes-not-reported-passes)
define the required behavior.

## Evidence register

CI records E-01–E-03 target implementation revision
`4c47e4bf9f3c603c9ae6853c82de1fb0f207d8da`, included in PR #24. They were retained against the historical PR #24 merge baseline `f2436a9`.
They remain the original executions, not reruns at the current baseline.
Times are UTC; later browser/live runs have separate entries.

| ID | Command and actual outcome | Time, environment and source |
|---|---|---|
| E-01 | `make lint`, `make test`, `make test-db`, `make poc`: passed; 12 Rust, 275 non-database Python and 236 PostgreSQL tests; offline fixture recovery/tamper rejection | [Foundation job](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38218166014/job/114707697759), 2026-10-12 07:30:55–07:33:58; Ubuntu runner, Python 3.14, Rust 1.99.0, PostgreSQL 17. Counts recorded in [Item 20](DEVELOPMENT.md#item-20--m72-exportreplay-recovery-integration); setup in [CI](../.github/workflows/ci.yml). |
| E-02 | `python scripts/check_deployment.py --recovery`: all 24 container groups passed; four recovery/export checkpoints; no live confirmation | [Container job](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38218166043/job/114707697872), 2026-10-12 07:30:55–07:34:38; report time 07:34:34.032559; Linux 6.17.0-1022-azure x86_64, Python 3.14.8, Docker 28.0.4, PostgreSQL 17, packaged real verifier. [Retained report](evidence/m7-recovery-4c47e4b.json). |
| E-03 | `npm ci --ignore-scripts --no-audit --no-fund`, `npm test`, `npm run build`: passed for the existing frontend | [Web job](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38218166014/job/114707697512), 2026-10-12 07:30:55–07:31:16; Ubuntu runner, Node 24. This is historical unit/build evidence; later browser evidence is recorded separately. |
| E-04 | Installed offline replay examples: valid `0/REPRODUCED`, tampered `1/FAILED`, scoped and missing-version `2/LIMITED`, unsupported-version `3/UNSUPPORTED` | Exact file hashes and CLI output in [replay-results.json](../fixtures/packets/replay-results.json). Reproduced byte-for-byte locally by 2026-10-12 12:09:30Z, macOS 27.0.1 arm64, Python 3.12.14, Rust 1.99.0, baseline `f2436a9` plus documentation-only changes; [Item 21](DEVELOPMENT.md#item-21--m72-release-evidence-consolidation). E-01 also runs CLI/engine regressions; E-02 runs downloaded authorized exports. |
| E-05 | `python scripts/validate_live_chain.py --output docs/evidence/m3-live-f8a594f.json`: live fixture recovery/refresh, fresh eligible merchant approval, identical refresh/approval retries and schema cleanup passed; no payment sent | Clean `f8a594fa7364a47fd94d961054b1f88429195b90`, 2026-10-12 13:23:24.163901–13:23:30.760930 UTC; Darwin 27.0.0 arm64, Python 3.12.14, PostgreSQL 17.11, Rust 1.99.0; QuickNode public demo, Zebra 6.4.2. [Run details](chain.md#recorded-live-run), [JSON](evidence/m3-live-f8a594f.json), [Item 22](DEVELOPMENT.md#item-22--m31-live-fixture-and-merchant-approval-validation). Real ASGI routes/in-process API client, real HTTPS RPC; not deployed ingress or browser acceptance. |
| E-06 | P4 recorded 8 actual-backend offline browser passes plus 1 separate simulated approval/retry/conflict pass; 8 frontend unit tests, build/typecheck and generated-contract check passed | [Original frontend handoff](frontend.md), merged in [PR #26](https://github.com/Kurisu-Labs/zecsolve/pull/26) as `8e8843d`; Windows, Node 24.19.0, Python 3.13.0, PostgreSQL 17.11, Rust 1.99.0, Chrome through Playwright. Original record provides a date, not exact UTC times or a retained machine report. Direct FastAPI TLS, not packaged nginx or Linux browser CI. |
| E-07 | `uv run --locked python scripts/check_deployment.py --recovery --browser`: 26 check groups passed, including all 8 offline browser scenarios through packaged nginx/TLS and all four export/replay recovery checkpoints | Clean `7d4ffcf49a4b9348be4c2034b1a2614f2ec6fa9e`; [container job](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38264285389/job/114862387139), October 12 14:40:20–14:45:32 UTC; browser 14:42:26.771594–14:43:35.849717. Linux 6.17 x86_64, Python 3.14.8, Node 24.21.0, Playwright 1.64.0 Chromium, Docker 28.0.4, PostgreSQL 17. [Retained JSON](evidence/m7-browser-recovery-7d4ffcf.json). |
| E-08 | `uv run --locked python scripts/browser_acceptance.py --simulated-chain`: 1 simulated approval/retry/cross-invoice conflict browser scenario passed, zero skips/retries | Same clean `7d4ffcf`; [simulated browser job](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38264285335/job/114862387270), October 12 14:39:10.486977–14:39:15.673935 UTC. Linux 6.17 x86_64, Python 3.14.8, Node 24.21.0, Playwright 1.64.0 Chromium, PostgreSQL 17, Rust 1.99.0. [Retained JSON](evidence/m7-browser-simulated-7d4ffcf.json). No live confirmation. |
| E-09 | `make lint`, `make test`, `make test-db`, `make poc`: passed, 12 Rust + 281 Python + 236 PostgreSQL tests. Frontend: 8 unit tests, generated-contract drift and build/typecheck passed | Same `7d4ffcf`; [foundation job](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38264285335/job/114862387291) and [web job](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38264285335/job/114862386925), October 12, Ubuntu/Python 3.14/Node 24/Rust 1.99.0. The native macOS timing failures remain recorded in [Item 23](DEVELOPMENT.md#item-23--m7-browser-ci-and-release-integration). |

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

### Browser CI artifact provenance

E-07 and E-08 preserve the downloaded artifact members byte-for-byte. Their ZIP
SHA-256 values were verified against GitHub before retaining the JSON:

| Evidence / artifact | ZIP SHA-256 | Retained JSON SHA-256 |
|---|---|---|
| E-07 / `11753943048`, `backend-recovery-evidence`, run `38264285389` | `c85adb6b070d95443319ce6a2c54513291407e27bff07c9eba213ad558921cd8` | `314c6062387eac1e64d89a43bcb6a2d33df4906db022cbe0c84d712e00ee581c` |
| E-08 / `11753928173`, `browser-simulated-evidence`, run `38264285335` | `7efc3cd7aaf773b829b62d77f588fbaee824929b4bb010048739aab17f8e9d4e` | `19b541d9b54b931abd752ba76b6bffd69f78d721b8a01afbc966258041ba1aa9` |

Both record `working_tree_changes=false`, `live_confirmation=false` and
`release_complete=false`. Browser certificate verification is disabled for the
generated localhost certificate; the separate deployment probes validate its
trust/hostname. No raw Playwright errors, DOM snapshots, credentials or downloaded
packets are retained. E-07's legacy nested `recovery.remaining_gates` is preserved
as emitted; it describes missing proof in that backend subroutine, not current
project status. The current harness labels this `outside_recovery_scope`; E-07's
outer browser result and E-05 supply separately attributed browser/live proof.
Neither file establishes target-specific operator controls or the complete release.

## A-01–A-15 traceability

Every row below has recorded backend evidence, with E-01 identifying the full
unit/database execution and E-02 identifying runtime checks. Named tests are
entry points within those runs, not newly claimed individual executions. To
repeat one, use `uv run --locked pytest path/to/test_file.py::test_name`; database
tests also require `ZECSOLVE_TEST_DATABASE_URL` for a disposable PostgreSQL
database. Preserve the full-suite command/result when using E-01 as evidence.

| ID | Demonstrated backend outcome and exact scenario | Evidence | Outstanding acceptance / owner |
|---|---|---|---|
| A-01 | Public Orchard fixture recovers 100,000 zatoshis; offline state remains unavailable. [test_verifier.py](../apps/api/tests/test_verifier.py): `test_mainnet_fixture_recovers_expected_fields`; E-02 public-fixture check. | E-01, E-02, E-05, E-07 | M3.1 merged in PR #27. P3 associates its recorded live revision and the final release bundle. |
| A-02 | Tampered OCK has no recovered output; txid/output-index failures stay distinct. [test_verifier.py](../apps/api/tests/test_verifier.py): `test_tampered_ock_is_invalid_without_recovered_fields`, `test_distinct_failure_reasons`; [demo test](../apps/api/tests/test_resolution_demo.py): `test_isolated_demo_uses_real_recovery_and_labels_simulated_credit` checks tampered approval denial. | E-01, E-07 | E-06 records tampered/missing browser evidence with zero credit; E-07 repeats it through nginx CI. |
| A-03 | Unapproved 100,000 on a synthetic 200,000 invoice gives 0 credited, 200,000 outstanding, 100,000 candidate/projected outstanding. [test_rules.py](../apps/api/tests/test_rules.py): `test_unapproved_recovery_is_only_a_projection`; [test_verification_api.py](../apps/api/tests/test_verification_api.py): `test_authenticated_invoice_to_evidence_verification_and_report`. | E-01, E-07 | E-06 records the actual-backend first workflow; E-07 repeats it through nginx CI. |
| A-04 | Synthetic 600,000 + 400,000 approvals cover 1,000,000. [test_resolution_safety.py](../apps/api/tests/test_resolution_safety.py): `test_two_synthetic_outputs_accumulate_to_full_balance`. These are synthetic accounting inputs. | E-01 | Backend scenario demonstrated; P3 retains its reference in the final revision's evidence. |
| A-05 | Same-output/key retries preserve the original decision and add no credit; recovery preserves accepted retries. [test_resolutions.py](../apps/api/tests/test_resolutions.py): `test_simulated_partial_approval_and_semantic_replay_are_atomic`; E-02 crash/database/restore retry groups. | E-01, E-02, E-07, E-08 | E-06 records evidence/noncredit retries and separate simulated approval retry; E-07/E-08 run both CI compositions. |
| A-06 | One winner for competing invoices; same-invoice concurrency commits once; conflict is opaque. [test_resolution_safety.py](../apps/api/tests/test_resolution_safety.py): `test_concurrent_two_invoices_one_output_has_one_winner_and_opaque_conflict`, `test_concurrent_same_output_same_invoice_commits_once`. | E-01; E-02 restored uniqueness, E-08 | E-06 records the simulated cross-invoice conflict; E-08 repeats its isolated CI case; P3 retains the final demo trace. |
| A-07 | Distinct output identities in one transaction allocate independently using synthetic rows. [test_postgres.py](../apps/api/tests/test_postgres.py): `test_two_outputs_in_one_transaction_can_be_allocated`. | E-01 | Backend scenario demonstrated; P3 retains its reference in the final revision's evidence. |
| A-08 | Missing, unsupported, unavailable and execution-error outcomes remain distinct from invalid evidence. [test_verifier.py](../apps/api/tests/test_verifier.py): `test_missing_evidence_and_missing_binary_are_not_invalid`, `test_unknown_consensus_branch_is_unsupported`, `test_invalid_transaction_data_does_not_accuse_receipt`, `test_subprocess_is_bounded`; [test_persisted_verification.py](../apps/api/tests/test_persisted_verification.py): `test_unsuccessful_attempts_are_persisted_honestly`. | E-01, E-07 | E-06 records missing/tampered/offline displays; E-05 records actual-source behavior. Final acceptance still preserves each negative backend outcome. |
| A-09 | Receiver/reference mismatch blocks eligibility; overpayment requires review. [test_rules.py](../apps/api/tests/test_rules.py): `test_recipient_and_memo_mismatch_block_matching`, `test_missing_reference_requires_review_without_unique_receiver`, `test_overpayment_requires_review`; [test_decision_rules.py](../apps/api/tests/test_decision_rules.py): `test_approval_gates_preserve_memo_overpayment_and_allocation_rules`. | E-01 | E-06 records candidate/partial-payment displays; retain remaining policy scenarios and reviewed UI evidence in the final bundle. |
| A-10 | Offline approval is denied and request fields cannot invent chain trust. [test_resolutions.py](../apps/api/tests/test_resolutions.py): `test_offline_approval_is_blocked_without_partial_decision`; [test_verification_api.py](../apps/api/tests/test_verification_api.py): `test_verification_and_report_require_ownership_and_reject_chain_spoofing`. RPC regression tests use synthetic responses; E-05 separately proves a real authorized refresh/approval and identical retries. | E-01, E-02, E-05 | M3.1 evidence merged in PR #27. Ongoing deployment requires explicit operator RPC configuration. |
| A-11 | Merchant isolation and customer/reviewer read/write/export scopes enforced. [test_resolution_safety.py](../apps/api/tests/test_resolution_safety.py): `test_foreign_merchant_and_wrong_case_cannot_decide`; [test_reviewer_reports.py](../apps/api/tests/test_reviewer_reports.py): `test_route_role_matrix_and_exact_component_response`; [test_exports.py](../apps/api/tests/test_exports.py): `test_export_http_permission_matrix_and_download_contract`. | E-01, E-02 scoped HTTPS checkpoints, E-07 | E-06 records all-role browser scenarios; E-07 repeats them through nginx CI. |
| A-12 | Expiry/revocation and evidence consent enforced, including after restore. [test_grants.py](../apps/api/tests/test_grants.py): `test_grant_authentication_checks_expiry_revocation_and_role`, `test_reviewer_selection_requires_actual_sharing_consent`; [test_exports.py](../apps/api/tests/test_exports.py): `test_revocation_during_export_decryption_prevents_disclosure`. | E-01, E-02 restored customer/reviewer revocation, E-07 | E-06 records disclosure, consent, revocation and session screens; final UI evidence must retain downloaded-copy limits. |
| A-13 | Authorized packets preserve exact components and historical context; scoped exports remain limited; concurrent export stays consistent; tampering fails. [test_exports.py](../apps/api/tests/test_exports.py): `test_merchant_export_replays_current_claim_consent_and_exact_evidence`, `test_export_snapshot_does_not_mix_concurrent_approval`; [test_replay.py](../apps/api/tests/test_replay.py): `test_real_recovery_and_both_historical_rules_reproduce_without_network`. | E-01, E-02 all four export/replay checkpoints, E-04, E-07 | E-06 records reviewer/merchant downloads and real replay; E-07 repeats deployed browser export and the four recovery checkpoints. |
| A-14 | Failed decisions leave no business rows; stale concurrent review is rejected; invoice/event history stays immutable. [test_resolution_safety.py](../apps/api/tests/test_resolution_safety.py): `test_failed_decision_rolls_back_all_business_records_but_keeps_refresh`, `test_different_outputs_serialize_and_require_fresh_review_before_overpayment`; [test_postgres.py](../apps/api/tests/test_postgres.py): `test_snapshots_and_events_reject_edits`. | E-01, E-02 migration/restore invariants, E-07 | E-06 records stale-version renewed review. P3 retains the final evidence reference; correction/version linkage remains outside P0. |
| A-15 | Actual TLS, request/process limits, disabled public POC/docs, readiness recovery and secret-canary log checks pass; restart/restore/export can be repeated. [Deployment procedure](deployment.md), [recovery checks and limits](recovery.md#what-is-exercised), [harness](../scripts/check_deployment.py). | E-01 deployment regressions, E-02, E-07 | E-06 records safe text rendering/keyboard/mobile/axe. E-07 repeats deployment/browser checks; operator controls and final demo/artifacts remain below. |

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
Add `--browser` after installing the [browser CI prerequisites](browser-ci.md) to run P4’s actual browser scenarios through the same deployed ingress. The offline browser scenarios execute before recovery seeds its globally allocated output; checkpoint recovery clients remain HTTP clients.

## Remaining handoffs and release decision

| Gate / owner | Evidence required to close it | Current state |
|---|---|---|
| M3.1 / operator + P3 | Operator selected the QuickNode public demo endpoint. E-05 records node/version/method compatibility, bound fixture/network/block/confirmation facts, freshness and the ordinary merchant approval trace. Follow [chain.md](chain.md#recorded-live-run). | Done for the recorded M3.1 run: PR #27 merged. Public demo availability is not an operating guarantee; final revision association remains explicit. |
| M6 and full M7.1 / P4, then P3 | P4 provides actual-backend merchant/customer/reviewer browser results, retry/conflict/session/negative paths, authorized export download, keyboard/responsive checks and screenshots. P3 associates them with the same-origin deployed revision and integrates deployment/CI changes if required. | P4 implementation/browser evidence merged in PR #26 (E-06). P3’s deployed browser/recovery and simulated CI passed (E-07/E-08); integration PR review/merge and reviewed UI screenshots remain handoffs. |
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
evidence is reviewed and merged. Browser CI and backend tests do not close the
remaining final-evidence, operator and team gates.
