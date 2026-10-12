# Browser CI and release integration

Person 3 integrates Person 4's merged [PR #26](https://github.com/Kurisu-Labs/zecsolve/pull/26)
suite into shared CI and the release rehearsal. Frontend behavior remains owned
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

The deployment suite paces API requests at 300 ms across the three browser
contexts, including automated fixture setup. Requests still use the ordinary
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

- `.cache/recovery-result.json` includes deployment/recovery and browser results;
  CI retains it as `backend-recovery-evidence`.
- `.cache/browser-simulated-result.json` records the separately labeled simulated
  case; CI retains it as `browser-simulated-evidence`.
- Reports record revision, working-tree state, UTC time, environment, scenario
  outcomes and proof limits. `live_confirmation=false` and
  `release_complete=false` are explicit. Old result files are removed before runs.
- Raw Playwright JSON, DOM error context, downloads, access codes, TLS/evidence
  keys and server diagnostics stay in a private temporary directory. They are
  never uploaded. Traces and screenshots remain disabled. `--keep-on-failure`
  retains private diagnostics locally for inspection; remove the retained test
  project/data afterwards. Share only reviewed, sanitized result files.

This closes the automation handoff when the integration PR is reviewed, CI passes
and it merges. Full release still requires the [operator/team evidence](release-evidence.md#remaining-handoffs-and-release-decision),
the final revision's assembled acceptance/demo and reviewed UI screenshots.
