# M7.2 technical release bundle and demo rehearsal

Person 3 owns this bundle. It assembles the technical release candidate and the
three PRD demo scenarios. **It is not a full-release approval:** actual target
acceptance, reviewed UI screenshots and team-supplied discovery/submission
artifacts remain outstanding. See the [handoff table](#remaining-release-handoffs).

## Candidate and provenance

The tested implementation candidate is
`775ca5d80956a79c836e9cccd209f26025af310a`, based on main
`ded49e1f6a38cd3d88bc475ed8c688dcf4acec9f` (merged PR #28).
Subsequent commits on `test/m7-final-release-bundle` assemble reports and docs.
This is a pinned candidate, not a claim about every future `main` or a deployed
image. After merge, record the merge SHA/image in the operator handoff; rerun
relevant checks if implementation changes.

Start with the [machine-readable inventory](evidence/m7-release-bundle.json).
It identifies each retained artifact by path, SHA-256, recorded revision, UTC
execution time, input classification and source. Reports are preserved as emitted;
file hashes establish identity, not independent attestation. The repository is
the bundle: no credentials, private packets, logs, dumps or `.env` files belong
in a release archive.

- [Demo rehearsal](evidence/m7-demo-775ca5d.json): three asserted scenarios,
  an authorized public-fixture export, six replay outcomes, fixture/license hashes
  and temporary-schema cleanup.
- [Authorized public demo packet](evidence/m7-public-demo-packet-775ca5d.json):
  exported by the ordinary merchant-authorized service from the newly created
  demo case, then replayed as `0/REPRODUCED`. Original receipt/transaction bytes
  match the public fixture exactly; invoice, actors and approval are synthetic.
- [Packaged browser/recovery](evidence/m7-browser-recovery-775ca5d.json): eight
  offline browser scenarios through nginx/TLS and four authorized export/replay
  recovery checkpoints (26 check groups).
- [Simulated browser](evidence/m7-browser-simulated-775ca5d.json): one isolated
  approval/retry/conflict scenario; explicitly simulated confirmation.
- [Live M3.1 trace](evidence/m3-live-f8a594f.json): historical run at `f8a594f`,
  using the operator-selected QuickNode public demo and public receipt. No new
  payment was sent. This bundle does **not** run live RPC again.
- [Acceptance index](release-evidence.md#a-01a-15-traceability) and
  [development log](DEVELOPMENT.md): precise test names, earlier runs and limits.

The M3.1 source revision is an ancestor of this candidate. There is no diff from
`f8a594f` to `775ca5d` in `apps/api/src/`, `apps/api/migrations/`, `crates/`,
`contracts/`, `Cargo.toml`, `Cargo.lock` or `scripts/validate_live_chain.py`.
This associates the existing live result with unchanged backend behavior; it
does not turn its October 12 observation into current chain state or prove the
final ingress/browser path used live confirmation.

## Acceptance coverage at this candidate

The inventory links the candidate's foundation/web CI and the retained reports.
Foundation runs the complete test sets; the exact test names for each row remain
in the [A-01–A-15 index](release-evidence.md#a-01a-15-traceability). A row below
identifies the tested behavior and its boundary, not a blanket production pass.

| ID | Recorded result at this candidate | Evidence / boundary |
|---|---|---|
| A-01 | 100,000-zatoshi historical recovery; unavailable chain offline | Foundation, demo; earlier M3.1 live observation separately retained |
| A-02 | Tamper/binding/index rejection; rejected invoice receives zero credit | Foundation, demo, packaged browser |
| A-03 | 0 credited, 200,000 outstanding, 100,000 candidate/projected shortfall | Foundation, demo, packaged browser |
| A-04 | 600,000 + 400,000 allocations cover 1,000,000 | Foundation synthetic aggregation test |
| A-05 | Retried approval adds no credit; accepted retries survive restarts/restore | Foundation, demo, simulated browser, recovery |
| A-06 | One winner for competing allocations; other invoice sees an opaque conflict | Foundation concurrency tests, demo, simulated browser |
| A-07 | Two selected outputs in one transaction can allocate independently | Foundation synthetic-row test |
| A-08 | Missing, unsupported, unavailable and execution errors remain distinct | Foundation negatives; browser missing/tampered/offline paths |
| A-09 | Binding mismatches block eligibility; overpayment requires review | Foundation policy tests; candidate UI checks, screenshots outstanding |
| A-10 | Offline/spoofed chain state cannot authorize credit | Foundation and demo; M3.1 historical live approval separately retained |
| A-11 | Merchant isolation and customer/reviewer read/write/export restrictions | Foundation, packaged browser, recovery permission matrix |
| A-12 | Consent and revocation enforced, including after restore | Foundation, browser, recovery; downloaded copies remain usable |
| A-13 | Authorized merchant packets reproduce; scoped packets stay limited; tampering fails | Foundation, browser download/replay, four recovery checkpoints; authorized public sample and six CLI examples |
| A-14 | Failed/stale decisions cannot partially allocate or rewrite history | Foundation transaction tests, browser stale review, recovery invariants |
| A-15 | TLS/limits/readiness/log checks, browser accessibility and recovery/demo pass | Packaged disposable environment; real target/operator controls outstanding |

## Reproduce the three-scenario demo

Use a clean checkout of the candidate, Python 3.12+, Rust 1.99.0, uv and a
disposable PostgreSQL 17 database. Follow [setup](../README.md#run-the-proof-of-concept)
and privately set `ZECSOLVE_TEST_DATABASE_URL` to a database whose role can
create/drop schemas. Do not use a customer/production database. Initial locked
dependency installation needs network access; the demo itself uses no RPC.

```sh
make setup
uv run --locked python scripts/rehearse_release.py
```

Success prints `PASS: three demo scenarios, authorized public export, six replay outcomes and fixture/license hashes`
and writes `.cache/release-rehearsal.json` plus `.cache/release-demo-packet.json`. The runner executes the real POC,
real application services in a temporary schema and the offline replay CLI.
It checks exact expected results; a mismatch/nonzero child failure stops the
run without a success report. Previous output is removed first. Raw child
stdout/stderr, generated credentials and temporary negative packet variants are
not retained. CI uploads the sanitized report and the known public/synthetic
export sample as `release-demo-evidence`. The demo accepts no case ID or private
evidence input; review any retained packet before sharing outside this workflow. The source demo removes its schema even on failure.

| Demo scene | Result to show | Explanation to give |
|---|---|---|
| 1. Underpayment/candidate | Synthetic invoice 200,000 zat (0.002 ZEC), recovered public output 100,000 zat (0.001 ZEC); 0 credited, 200,000 outstanding and 100,000 projected shortfall | Recovery is real; the invoice is synthetic. Offline recovery cannot authorize credit. |
| 2. Retry/conflict | Explicitly simulated approval credits 100,000 and leaves 100,000 outstanding. Retry returns the same resolution. Second invoice receives `OUTPUT_ALLOCATION_CONFLICT`. | The ordinary resolution service enforces the accounting rules. The injected confirmation is test-only, not evidence of a new payment or live inclusion. |
| 3. Invalid evidence | `INVALID` / `OUTPUT_RECOVERY_FAILED`; approval denied; rejected invoice stays at 0 credited | Invalid supplied evidence does not establish customer fraud. No automatic credit. |
| Review/export coda | Complete v1/v2 `0/REPRODUCED`; tampered `1/FAILED`; scoped/missing-version `2/LIMITED`; unsupported-version `3/UNSUPPORTED` | Checked-in packets combine public crypto evidence with synthetic history. The newly generated public sample uses the real merchant export service and reproduces. Actual authorized HTTP exports are proven separately by browser/recovery evidence. |

For individual commands and the original service trace, use the
[offline demonstrations](release-evidence.md#repeatable-demonstrations-without-rpc).
To replay the retained authorized sample directly:

```sh
uv run --locked replay-case docs/evidence/m7-public-demo-packet-775ca5d.json --verifier target/debug/zecsolve-verifier
```

Expect exit 0/`REPRODUCED`; its simulated observation remains a historical external
assertion, not fresh chain proof. Do not regenerate or overwrite the retained reports; retain a new file with its
own revision/time if repeating the run.

### Presentation cue sheet (not a recorded video)

- **0:00–0:20:** Explain the merchant's exception case and the four evidence
  layers: claim/invoice, recovered output, external observation, merchant decision.
- **0:20–0:55:** Show scene 1 and exact zatoshi balances. State public receipt,
  synthetic invoice, offline observer and no new ZEC payment.
- **0:55–1:35:** Show scene 2, pointing out `SIMULATED`, unchanged credit on retry
  and the opaque second-invoice conflict.
- **1:35–2:00:** Show scene 3 and the unchanged rejected-invoice balance.
- **2:00–2:35:** Show the public authorized sample and its `REPRODUCED` result, scoped
  replay limits, and separately recorded HTTP export/browser evidence. A restricted packet cannot claim a complete replay.
- **2:35–2:55:** Attribute Glasspane; identify the prior live run and outstanding
  operator/team gates. Stop short of claiming a public deployment or market demand.

This is an English narration/rehearsal aid. P4/team still supply reviewed UI
screenshots and the actual presentation/demo recording. For a browser walkthrough,
use [browser-ci.md](browser-ci.md); never insert simulated authority into the
production deployment. The live approval is shown as the earlier recorded trace,
not impersonated by the simulated demo.

## Limitations and attribution

Glasspane `gp-core`/`gp-types` and the public fixtures are reused at pinned revision
`f6468e6d08a7adad53bf2991a311358dc84e869b`; see the
[manifest](../fixtures/manifest.json) and [MIT license](../third_party/glasspane/LICENSE).
Zecsolve contributes adapters, evidence/consent handling, invoice/accounting rules,
authorization, reports/replay, UI and deployment orchestration. Receipt recovery
does not establish payer identity, intent, invoice truth or approval. Hashes do
not authenticate an author, and offline replay does not prove fresh inclusion.

The demonstrated historical fixture is mainnet Orchard. Mainnet receipt v0 and
v5 transaction branches NU5–NU6.2 are the current compatibility boundary. There
is no historical Sapling end-to-end fixture or Ironwood claim. Public QuickNode
demo availability is not an operating guarantee; a real deployment must explicitly
configure and validate its chosen source. Browsers disable certificate validation
for the generated local certificate; separate deployment probes verify its
trust/hostname. Synthetic observations and business records remain labeled.

Recovery demonstrates disposable restart/restore and exact authorized exports,
not production backup service, PITR, offsite custody or a recovery-time guarantee.
Revocations/writes newer than a backup need reconciliation before reopening access.
Private customer use additionally requires retention/deletion/purge terms across
original and derived data, histories and backups. These restrictions do not
prevent the public-fixture demo. See [recovery](recovery.md) and
[security](security.md) for the full limits.

## Remaining release handoffs

| Owner | State | Concrete evidence required |
|---|---|---|
| P3 / reviewer | Pending PR review/merge | Review this bundle, final branch CI and lineage; after merge bind the chosen image to the actual merge SHA. Branch creation/code alone is not completion. |
| Operator + P3 | Not run on a real target | Host/domain and exact image; TLS/access provisioning; explicit RPC configuration; encrypted volume; external evidence/backup-key custody; actual backup/restore record and recovery/revocation reconciliation. No target is selected here. |
| P4 | Not supplied | Reviewed merchant/customer/reviewer screenshots showing disclosure, permission and proof limits, with revision/time/scenario attribution. Automated browser results are already recorded. |
| Team lead + team | Not supplied | Two genuine merchant/provider discovery notes (including negative feedback/evidence availability), English presentation/demo recording, and registration/submission confirmation. P3 indexes supplied artifacts; no outreach or submission occurs in this task. |
| Operator + team | Separate private-pilot prerequisite | Retention/deletion/purge process covering originals, derived fields, business history and backups. Not required for the current public-fixture demonstration. |

Use the [evidence handoff fields](release-evidence.md#remaining-handoffs-and-release-decision):
owner, A-IDs, exact revision/image, UTC time, environment, command/scenario, actual
outcome, input classification, sanitized artifact path/hash and CI/PR link, limits.
Missing evidence remains `not supplied` or `not run`; do not turn it into a pass.
This bundle closes P3's assembly/rehearsal slice only after review/CI/merge. Full
M7 remains incomplete until the required operator/team artifacts are accepted.
