# Vercel public-fixture deployment

The demo is live at **https://zecsolve.vercel.app** on Vercel Hobby with a Neon
Free PostgreSQL database in Singapore. One container serves Person 4's built
Vue app, the Python API and the pinned native Rust verifier under the same
origin. This is a public-fixture demonstration; no ZEC was sent during setup.

## Recorded target

| Item | Value |
|---|---|
| Application revision | `c721aea6ee2e3b7379bd19d90f70fbecb6f06da2` |
| Deployment | `dpl_9KuhxWXxFjhPX8fCZSZ4XUXFYBoU` |
| Container digest | `sha256:d09d502b23856c0db12862a976111d8173e5fac9c8112d5199209156b015adb9` |
| Runtime / database region | `sin1` / Singapore |
| Database | Separate `zecsolve-demo` Neon Free resource; migrations `0001`–`0009` applied |
| RPC | Operator-selected QuickNode public demo; source ID `quicknode-public-demo` |
| Evidence | [Sanitized hosted checks](evidence/vercel-deployment-c721aea.json) |
| Repository validation | [Foundation/web/simulated browser CI](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38283817789), [deployment/browser/recovery CI](https://github.com/Kurisu-Labs/zecsolve/actions/runs/38283817800), both passed for the deployed code |

The hosted checks used real HTTPS cookie sessions and the existing public
Glasspane mainnet receipt. Customer claim/evidence submission and identical
retry passed. Verification recovered 100,000 zatoshis; actual RPC confirmation
supported a fresh merchant approval. Repeating approval preserved one decision
and 100,000 credited / 100,000 outstanding. Merchant export replay returned
`REPRODUCED`; scoped reviewer replay returned `LIMITED`. Customer report,
export and approval were denied; revoked grants invalidated their sessions.
The two temporary test grants were revoked. The operator-approved merchant
credential remains private and expires after 30 days.

Browser smoke checked sign-in, case listing, the live case and session
restoration. The existing browser suite passed separately through Compose in
CI; it was not rerun as a full suite against the shared hosted database.
A P4 follow-up remains: the case screen shows the historical offline
"Chain not verified" finding alongside the later confirmed chain/approved
credit. Hosted API balances, approval observation and packet replay passed;
this display ambiguity is not presented as a completed UI review.

## Runtime and configuration

[vercel.json](../vercel.json) explicitly registers one `container` service and
routes all paths to it. [Dockerfile.vercel](../Dockerfile.vercel) shares its
build stages with Compose; Vercel uses its final `vercel` stage. The initial
attempt without explicit service routing returned 404 and was replaced by the
working deployment above. Dashboard "Ready" alone is not an application check.

[Vercel containers](https://vercel.com/docs/functions/runtimes/container) and
[Services](https://vercel.com/docs/services) are beta features available on all
plans at the time of this deployment. The project uses official CLI 63.1.2
because [Hobby cannot connect Git organization repositories](https://vercel.com/docs/limits),
including public ones. The GitHub repository remains in `Kurisu-Labs`; it was
not copied to a personal repository. Git pushes do **not** deploy this project
automatically.

Set these in **Production** environment variables; the database integration is
connected only to Production. Secret values must be entered through private
stdin/dashboard fields, never command arguments, build arguments or Git.

| Variable | Configuration |
|---|---|
| `PORT` | `8000` |
| `ZECSOLVE_DEPLOY_HOST` | `zecsolve.vercel.app` |
| `ZECSOLVE_BROWSER_ORIGINS` | `["https://zecsolve.vercel.app"]` |
| `ZECSOLVE_DATABASE_URL` | Neon pooled URL with `postgresql+psycopg` driver and `sslmode=verify-full`; secret |
| `ZECSOLVE_EVIDENCE_KEY_ID` | `vercel-demo-v1` |
| `ZECSOLVE_EVIDENCE_KEY` | Base64 of 32 random bytes; secret; retain across releases |
| `ZECSOLVE_RPC_URL` | `https://docs-demo.zec-mainnet.quiknode.pro/` |
| `ZECSOLVE_RPC_SOURCE_ID` | `quicknode-public-demo` |
| `ZECSOLVE_RPC_TIMEOUT_SECONDS` | `30` |

The runtime requires Vercel production/preview context and an exact origin,
uses `certifi` trust roots with full PostgreSQL certificate/hostname
verification, and refuses a schema that differs from the packaged Alembic
head. `sslrootcert=system` alone failed with bundled libpq on the tested
machines; verification was retained by providing the packaged CA bundle.

Vercel's managed HTTP ingress is the exclusive route to this container. Only
this entrypoint trusts all forwarded proxy peers; **do not run it as a directly
exposed Docker/VPS server**. The [Compose profile](deployment.md) retains its
single fixed trusted proxy IP. Host, HTTPS, Origin, CSRF and role checks remain
inside the application. The runtime disables POC/docs and access logging, uses
safe runtime error records, one worker, 32 concurrent tasks and the existing
bounded verifier/body limits. TLS is provided by Vercel. No container-local
file or volume is used for durable application data.

Compose's nginx per-IP rate limits, read-only filesystem, PID limits and fixed
CPU/memory budgets are **not** inherited by Vercel. Provider function limits
and scaling apply instead. Host-wide custom rate-limit/capacity acceptance is
still an operator task; the hosted smoke is not a load or abuse-resistance test.

## Release and access procedure

1. Complete the repository branch/PR checks and select the reviewed revision.
   Authenticate the official Vercel CLI and link the existing `zecsolve`
   project in the operator's scope. Do not create a second database/project for
   a routine release. `.vercel/`, `.env*` and `.cache/` are ignored by uploads.
2. Before a schema-changing release, record a backup/recovery point and apply
   migrations once as an operator action, using Neon's **direct/unpooled** URL.
   Keep its password URL-encoded, select the `postgresql+psycopg` driver and
   `sslmode=verify-full`, and set its `sslrootcert` query parameter to the path
   returned by `certifi.where()` on that operator machine. Load the URL privately
   into `ZECSOLVE_DATABASE_URL`; from the repository root run
   `uv run --locked alembic upgrade head`. Capture diagnostics privately and
   check success before continuing. Cold starts do not perform migrations.
3. Deploy the clean checkout with the official CLI, for example:
   `npm exec --yes --package=vercel@63.1.2 -- vercel deploy --prod --yes`.
   Confirm the linked project/scope first. Preserve the returned deployment ID,
   Git revision and image digest. A code rollback must remain compatible with
   the current schema; promoting an older image does not undo migrations.
4. Check HTTPS `/`, `/connect` with HTML Accept, and `/health/ready`; anonymous
   `/api/cases` and `/api/session` must return 401, while POC/docs return 404.
   Test secure session exchange, authorized fixture workflow and export/replay
   with an explicitly provisioned demo merchant. Preserve idempotency keys on
   retries; the historical fixture output can be credited only once per
   deployment, so reuse its existing case for inspection and do not expect
   another invoice to accept the same output.
5. Use the existing [operator credential CLI](access.md) with the private direct
   database configuration for issuance/revocation. Capture its one-time JSON
   output into a private file. Users enter that code at `/connect`; never put
   it in a link, shared report, frontend bundle or screenshot. Grant permissions
   remain server-derived. Preview deployments need their own database, secrets
   and exact hostname/origin; do not share the Production database with them.

The first deployment's local handoff files are in ignored
`.cache/vercel-private/` (directory mode 0700, files 0600), including
`merchant-access-code.txt`, `merchant.json` and `evidence-key`. These are local
operator materials, not a backup system. Keep an independent encrypted copy of
the evidence key and its ID; losing it prevents decrypting existing evidence.
Do not regenerate that key during deployment. Key rotation/multi-key recovery
requires a planned procedure, not a changed environment value.

## Remaining operating gates

Vercel Hobby is for [personal, noncommercial use](https://vercel.com/docs/plans/hobby).
No paid upgrade was enabled. The selected Neon Free plan currently provides
[1 GB storage and 100 CU-hours per project per month](https://neon.com/blog/neon-free-plan-1-gb-per-project);
check provider dashboards before wider usage. Scale-to-zero and public demo
RPC availability can add latency or block new credit. This setup has no
availability guarantee.

Hosted backup/restore, external key custody, provider storage/encryption
controls, recovery-point/recovery-time expectations, revocation reconciliation
after restore and host-wide rate controls still require target-specific
acceptance. Earlier Compose restore evidence does not validate restoring Neon.
Reviewed P4 screenshots, the display follow-up above and team discovery/demo/
submission artifacts remain separate handoffs. Retention/deletion terms and an
authorized purge process are required before private customer evidence. See
[remaining release gates](release-evidence.md#remaining-handoffs-and-release-decision).
