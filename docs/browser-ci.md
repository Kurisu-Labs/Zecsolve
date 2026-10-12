# Browser CI and release integration

Person 3 integrated Person 4's merged [PR #26](https://github.com/Kurisu-Labs/zecsolve/pull/26)
suite into shared CI and the release rehearsal in [PR #28](https://github.com/Kurisu-Labs/zecsolve/pull/28). Frontend behavior remains owned
by Person 4; the integration changes only test origin/request scheduling and
runner wiring. No application, authorization, database schema or chain policy
changes are needed.

## Two explicit boundaries

| Command / CI job | Actual execution | Limits |
|---|---|---|
| `uv run --locked python scripts/check_deployment.py --recovery --browser` / `container-smoke` | Eight offline Chromium scenarios through the packaged Vue build, nginx TLS ingress, real API, PostgreSQL and Rust verifier, followed by the four recovery/export checkpoints | Public fixture and synthetic application data; production offline observer, zero live credit. Browser certificate verification is disabled for the generated localhost certificate; the Python deployment checks independently verify certificate trust and hostname. |
| `uv run --locked python scripts/browser_acceptance.py --simulated-chain` / `browser-simulated` | One approval/lost-response retry/cross-invoice conflict scenario using P4's isolated HTTPS test composition and the real backend/verifier | Explicit `SIMULATED` observer and test-only authority. This composition never enters the deployment image or proves live inclusion. |

The default suite covers merchant/customer/reviewer sessions, consent, restricted
reads/actions, exact evidence and authorized downloads, real offline replay of a
downloaded merchant packet, response-loss retries, stale review, missing/tampered
evidence, pagination/filtering, keyboard/mobile/axe checks and session failure
states. The simulated scenario separately checks one 100,000-zatoshi credit and
an opaque second-invoice conflict. See [P4's original evidence](frontend.md) for
the scenario detail and original environment. M3.1's [live trace](chain.md#recorded-live-run)
remains separately attributed; neither CI composition uses an RPC endpoint.

The deployment suite installs a 300 ms API scheduler across the three browser
contexts, including automated fixture setup. The page-level response-loss handlers
use their own routing and bypass that scheduler; see the investigation below. Requests still use the ordinary
network and server; production's 5-request/second ingress limit stays unchanged
and its rejection behavior is separately tested by the deployment harness.
All contexts use the generated deployment origin rather than a fixed port.
Browser scenarios run before the recovery harness seeds a simulated allocation:
the output uniqueness constraint is global, so a different merchant alone would
not isolate that fixture. No allocation is removed or constraint bypassed.

## Reproduce

Use Node 24+, Python 3.12+, the locked Python/Rust environment from `make setup`,
Docker/Compose, OpenSSL, and Chromium:

```sh
make setup
npm --prefix apps/web ci --ignore-scripts --no-audit --no-fund
cd apps/web
npx playwright install --with-deps chromium
cd ../..
uv run --locked python scripts/check_deployment.py --recovery --browser
```

The deployment command builds the frontend inside the image and creates its own
loopback-only database, merchant, secrets and TLS files. It removes its Compose
project and volume afterwards. Local replay of the browser-downloaded packet
uses the same checkout's real Python engine and `target/debug/zecsolve-verifier`.
Recovery checkpoint replay additionally runs in the network-disabled container.

For the separate simulated case, build the host frontend and privately set
`ZECSOLVE_TEST_DATABASE_URL` to a **disposable** PostgreSQL database ending in
`_browser`, with permission to create schemas. Port 8443 must be free:

```sh
npm --prefix apps/web run build
uv run --locked python scripts/browser_acceptance.py --simulated-chain
```

The runner starts/stops P4's server automatically. The database must be discarded
after the rehearsal (CI destroys its service container); the existing server
creates a random schema per run. Without `--simulated-chain`, the runner executes
the eight offline scenarios against P4's direct HTTPS server, useful locally but
distinct from nginx deployment acceptance.

## Evidence and failure handling

Both jobs require exactly the selected scenarios to pass with zero skips,
failures or retries; `test.only` is rejected. The web job also runs
`npm run types:check` against the published schemas. The repository checks remain
required in addition to browser acceptance.

- `.cache/recovery-result.json` includes successful deployment/recovery and browser
  results; CI retains it as `backend-recovery-evidence` only after success.
- `.cache/browser-deployment-result.json` is independent of recovery completion;
  CI retains it as `browser-deployment-evidence` even when browser acceptance fails.
- `.cache/browser-simulated-result.json` records the separately labeled simulated
  case; CI retains it as `browser-simulated-evidence` even when acceptance fails.
- Reports record revision, working-tree state, UTC time, environment, scenario
  outcomes and proof limits. Browser schema version 1 adds explicit `outcome`,
  fixed `reason`, exit code, per-attempt status/retry/duration, and source locations
  limited to the known public spec. Only reviewed scenario titles are retained;
  unknown titles become `unknown scenario` and fail acceptance. Messages, stacks,
  snippets, arbitrary paths, stdout/stderr, attachments and payloads are excluded.
  Malformed reports and missing/duplicate attempts fail closed. Server/deployment
  setup failures are labeled `setup_failed` when caught before browser execution.
  A successful browser artifact does not imply that subsequent recovery passed.
  Upload steps run after failures only when their exact sanitized file exists; a
  cancelled job, killed runner or failure before the harness starts may have no report.
  `live_confirmation=false` and
  `release_complete=false` are explicit. Old result files are removed before runs.
- Raw Playwright JSON, DOM error context, downloads, access codes, TLS/evidence
  keys and server diagnostics stay in a private temporary directory. They are
  never uploaded. Traces and screenshots remain disabled. `--keep-on-failure`
  retains private diagnostics locally for inspection; remove the retained test
  project/data afterwards. Share only reviewed, sanitized result files.

The automation handoff merged in PR #28 after all four CI jobs passed. The
[release bundle](release-bundle.md) records a fresh run at its pinned candidate. Full release still requires the [operator/team evidence](release-evidence.md#remaining-handoffs-and-release-decision),
target-specific acceptance and reviewed UI screenshots. The technical bundle/demo
rehearsal merged in [PR #29](https://github.com/Kurisu-Labs/zecsolve/pull/29).

## PR #29 intermittent browser failure investigation

The original cause remains **undetermined**. At unchanged head `4d078c9`, the
[push attempt 1](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38271675020/attempts/1)
passed all ten deployment control groups, then job `114887171986` failed at
2026-10-12 15:42:30 UTC with the generic browser exception. The old runner raised
before parsing Playwright JSON; cleanup deleted the private report, and no
failure artifact was uploaded. The failed scenario/assertion is unrecoverable
from the retained CI evidence. The independently triggered
[PR run](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38271763432) and
[push attempt 2](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38271675020/attempts/2)
passed the same head. Those passes do not establish the failure's cause.

Diagnostics revision `a362619` leaves P4's scenarios, timeouts, assertions,
production ingress limits and zero-retry policy unchanged. Two fresh local
packaged runs passed all eight scenarios with zero skips/retries: 2026-10-12
16:10:08–16:11:10 UTC (61,583 ms; followed by all 26 deployment/recovery groups)
and 16:13:35–16:14:36 UTC (60,540 ms; deployment/browser only). Both used clean
`a362619`, macOS 27.0.1 arm64, Python 3.12.14, Node 26.11.0 and Playwright 1.64.0.
Each run used a new disposable database/merchant/project; both cleaned up.

The unchanged code also passed Linux CI: [foundation/web/simulated browser](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38275414758)
and [packaged browser/recovery](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38275414753).
The latter passed all 26 groups and eight browser cases (66,824 ms); the simulated
case passed separately (4,984 ms). There were zero retries/skips. The exact
[deployment report](evidence/browser-diagnostics-deployment-a362619.json) and
[simulated report](evidence/browser-diagnostics-simulated-a362619.json) are retained
unchanged from artifacts `11758733105` and `11758413779`. Their SHA-256 values are
`215a9afd425a8957c1a35221ec1f25b21e0a35bf10b934e5c6b6423ec9ab9dcd` and
`2eb4a3d02c5d3dd85ef3933e0af1333fddfaeded5bb0be15dfd9e4d10eb78ce0` respectively;
artifact archive digests were verified before extraction. Only the named JSON
member was present in each archive. These are passing observations, not proof
that the intermittent failure is fixed.

A deliberate assertion failure in a temporary standalone Playwright spec also
returned exit 1 and retained the reviewed scenario name and assertion line 3.
The raw error contained a secret canary; the sanitized output did not. The
private probe directory was removed. This tests failure reporting, not product
acceptance or reproduction of the original failure. The 26 regression cases
also cover failed/malformed JSON, startup/timeout, stale success removal, false
success on a nonzero exit, empty/retried/skipped/flaky selections and private
path/message/attachment exclusion.

Code inspection identifies two **unconfirmed** timing candidates for P4 triage:

- In the three-role scenario, reviewer refresh follows the merchant revoke click
  without awaiting the revoke acknowledgement (`workflow.spec.ts:228–234`). A
  delayed commit could let that refresh see the still-valid grant. If diagnostics
  point here, delay the revoke request before forwarding it and synchronize on
  the successful server/UI acknowledgement while retaining the denial assertion.
- The response-loss handlers (`workflow.spec.ts:148–155`, plus grant/decision
  variants) call `route.fetch`/`route.continue` instead of traversing the context
  scheduler. If the failure points at one of these retries, inspect the private
  response status for a real 429 before changing request scheduling. The separate
  production limit/rejection checks must remain intact.

Neither candidate was observed failing in these runs or proven responsible for
PR #29. P3 changes only runner/CI diagnostics; P4 retains frontend scenario
ownership. Do not infer a rate-limit or application bug from an unchanged rerun
passing, and do not add retries or relax assertions to hide a failure.

On the next failure, download the job's sanitized browser artifact, check
`outcome`, `reason`, `exit_code`, the failed scenario and `error_locations`, and
inspect that exact source revision. `process_failed` with no parsed counts can
mean no usable JSON was produced; `runner_timeout` and `process_start_failed`
identify harness failures. Reproduce with the same command and `--keep-on-failure`
only in a disposable local environment when private details are needed. Never
upload that raw directory; remove retained Compose volumes/secrets after review.
