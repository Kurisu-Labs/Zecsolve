# zecsolve web

Vue 3 + TypeScript + Tailwind v4 frontend owned by Person 4. The app supports merchant workflows, scoped customer submissions, reviewer disclosures, and authorized packet downloads.

## Build and checks

Use Node.js 24 or newer:

```sh
cd apps/web
npm ci
npm test
npm run types:check
npm run build
```

The build includes Vue/TypeScript checking and writes `apps/web/dist/`. Person 3's deployment composition serves that directory alongside `/api` on one HTTPS origin. See [deployment](../../docs/deployment.md).

`npm run types:api` regenerates `src/api/contracts.d.ts` from the backend's published JSON schemas under `contracts/`, without a running server. `types:check` detects drift. `types.ts` retains the narrower merchant/demo presentation types; the new session, listing, grant, submission, reviewer and packet operations consume generated types.

## Access and workflows

- `/connect` exchanges a manually entered credential/grant code for a browser session. A `#code=` fragment is removed before exchange, including when Connect is already open. Query-string codes are ignored and removed. Credentials are not saved in localStorage; values left by the previous frontend are deleted.
- Requests use same-origin cookies. Mutations send the session-bound `X-CSRF-Token`. Restoration, logout, local expiry and server 401 responses recover safely. Another code can replace access when the CSRF cookie is missing.
- Merchant `/cases` uses backend pagination and state filters. `/cases/new` saves immutable invoice terms and opens a case. Case detail separates claims, receipt recovery, chain observations and decisions; it supports evidence verification/selection, chain refresh and explicit decisions.
- `/cases/:id/grants` creates/lists/revokes customer/reviewer access. Report sections, selected original evidence and export permission are separate. Only evidence with explicit reviewer sharing consent can be selected. A creation retry does not redisclose a lost code.
- Customer `/submit/:id` records a claim or optional receipt/raw transaction, processing authorization and optional reviewer sharing (unchecked by default). Its only response is the submission acknowledgement. It never requests merchant reports, evidence reads, verification or decisions.
- `/review/:id` renders the sections actually returned for the reviewer. Notes, memos and reasons are text. Authorized component downloads preserve exact UTF-8 text; textarea previews can normalize line endings.
- Merchant and export-enabled reviewer downloads use `CasePacketV1` from the export API. Full-history and limited packets have explicit labels. Print remains a report view. Downloaded copies cannot be recalled.

Pending mutations retain only an actor/route/body digest and random retry key in sessionStorage, with an in-memory fallback. Codes and original evidence are not stored there. Unchanged requests after response loss reuse their key; changed requests have separate identities. Stale decisions require explicit review after refreshing the case.

Demo mode is selected explicitly on Connect or a public demo scenario and persists as a per-tab preference. Public fixture outcomes and synthetic confirmations are labeled. Demo actions do not establish live inclusion or real credit.

## Development

`npm run dev` runs Vite on port 5173, proxying `/api` to `127.0.0.1:8000`. Demo development works over HTTP. Real session integration requires HTTPS and an exact `ZECSOLVE_BROWSER_ORIGINS` value; use the deployment composition or the browser harness below. There is no insecure-cookie bypass.

## Actual-backend browser acceptance

The suite uses the built app, real FastAPI deployment boundary, PostgreSQL migrations/services and Rust verifier. Lost-response tests commit the real request and abort only its response. Traces and automatic screenshots are disabled to avoid retaining access codes/evidence.

From the repository root, prepare Python and the verifier (`make setup` with supported Linux tooling), build the frontend, and create a disposable PostgreSQL database named with an `_browser` suffix. In the server terminal:

```sh
export ZECSOLVE_TEST_DATABASE_URL='postgresql+psycopg://zecsolve:zecsolve@127.0.0.1:5432/zecsolve_browser'
export ZECSOLVE_BROWSER_SCRATCH='/tmp/zecsolve-browser'
uv run python apps/web/tests/browser_server.py
```

Each server start creates a fresh schema, a private synthetic merchant code, and local TLS files in the scratch directory. Keep that directory outside the repository and never publish its contents. In another terminal:

```sh
export ZECSOLVE_BROWSER_STATE='/tmp/zecsolve-browser/state.json'
export ZECSOLVE_BROWSER_CHANNEL='chromium'
cd apps/web
npx playwright install chromium
npm run test:browser
```

Installed Chrome is the default channel. On Windows use PowerShell `$env:` equivalents and a local scratch path. Set `ZECSOLVE_BROWSER_VERIFIER` when using another binary location. Native Windows uses a harness-only bounded pipe transport because the production adapter's POSIX selectors cannot read Windows pipes; the bridge still executes the real Rust binary.

The default offline run skips only the simulated approval/conflict case. Stop the server, restart it with `--simulated-chain`, and run:

```sh
npm run test:browser -- --grep 'simulated approval'
```

That source is visibly labeled and exists only in test composition. It does not satisfy Person 3's live RPC gate. The local eight-hour expiry scenario advances the browser clock; revocation uses the actual backend.

See [frontend verification and handoff](../../docs/frontend.md). Person 3 owns registering this browser suite in shared CI/release wiring.

## Source map

| Path | Purpose |
|---|---|
| `src/api/client.ts`, `session.ts`, `access.ts`, `retry.ts` | Cookie transport, role navigation and safe retries |
| `src/api/contracts.d.ts` | Generated backend contracts |
| `src/api/store.ts`, `fixtures.ts`, `rules.ts` | Merchant presentation and selected public demo |
| `src/pages/` | Access, case listing/creation/detail, grants, submission and reports |
| `src/components/SubmissionForm.vue` | Consent and acknowledgement flow |
| `src/components/ExportButton.vue`, `ReportFields.vue` | Authorized downloads and text disclosure rendering |
| `tests/browser/`, `tests/browser_server.py` | Browser-to-API-to-database acceptance |

Keep exact integer-zatoshi arithmetic, distinct evidence layers, keyboard access, labeled errors, responsive layouts and reduced motion. Yellow is the disclosure/approval accent. Keep WebGL and motion libraries lazy. TypeScript casts belong in script sections, not templates.


## Shared CI and deployment handoff

P4's integration and recorded browser results merged in PR #26. P3's
[browser CI runner](../../docs/browser-ci.md) executes this suite through the
packaged nginx deployment with a generated `ZECSOLVE_BROWSER_URL` and private
state. `ZECSOLVE_BROWSER_API_INTERVAL_MS=300` schedules automated API requests
below the unchanged ingress budget. The existing localhost defaults still work.
The separate simulated job uses the original `--simulated-chain` composition.
Only sanitized result JSON is uploaded; raw diagnostics/downloads stay private.
