# Person 4 frontend integration and browser evidence

The user explicitly resumed Person 4's frontend scope on October 12, 2026 and authorized implementation/testing locally when GitHub authentication prevented publishing the task branch. The local branch is `feat/m6-frontend-integration`, validated against main through `640b1b1` (PR #23 export merge), then synchronized with `4066ec8` (PR #25 release-evidence merge) before publication and `7853d3f` (PR #27 live-validation evidence merge) while resolving PR #26 conflicts. Contributor identity beyond the Person 4 slot has not been specified.

## Implemented scope

M6.0–M6.5 merged in PR #26: generated published-contract types; cookie sessions and CSRF; role-aware navigation; merchant case listing/pagination/filtering and invoice/case creation; evidence verification/selection, chain refresh and explicit decisions; grant creation/list/revocation with consent-aware evidence selection; scoped customer claims/evidence and acknowledgements; selected reviewer reports/original components; authorized full-history/scoped packet downloads and printable merchant/reviewer reports. This preserves the established Vue/Tailwind design and explicitly selected public demo.

Original files are read as UTF-8 without trimming or line-ending conversion. Preview controls may normalize line endings, so original component downloads use the actual returned strings. Packet receipt components are compared to the source bytes after base64 decoding. Notes/reasons/memos render as text. Reviewer statuses, dates, limits and currency have readable display labels; print uses a light layout with navigation/download controls hidden. Customer routes never follow acknowledgements with merchant reads.

Mutation recovery stores only request digests and random retry keys. Browser tests drop a real response after commit and confirm that the unchanged request reuses its key. Lost grant codes are not regenerated. Stale decisions refresh the case and require another explicit review. Simulated chain observations are labeled in case tiles, demo listings and printable reports.

## Evidence recorded October 12, 2026

Environment: native Windows; Node.js 24.19.0; Python 3.13.0; PostgreSQL 17.11 on a dedicated disposable loopback database; Rust/Cargo 1.99.0; installed Chrome through Playwright. The built frontend was served by the actual FastAPI deployment boundary at `https://localhost:8443` with generated local TLS, real migrations/services, encrypted fixture evidence and the freshly built Rust verifier. Each harness start creates a fresh schema.

| Check | Result and limits |
|---|---|
| Frontend unit/workflow tests | 8 passed: role/case isolation, CSRF cookie selection, retry identity isolation, integer currency, approval request semantics, verification references, observation history and partial payment state |
| Vue/TypeScript + production build | Passed; output remains `apps/web/dist/` |
| Published-contract generation/drift | Regenerated after M5 merge; checked against published schemas |
| Default offline browser suite | 8 passed; the isolated simulated case is intentionally skipped in this composition |
| Simulated approval/conflict browser case | Passed separately with `--simulated-chain`; this does not prove live chain inclusion |
| Rust verifier suite | 12 passed after building with debug symbols disabled and one build job |
| Formatting/lint | Rust fmt/clippy and Python ruff passed; no backend production code changed in this frontend branch |
| General native-Windows Python backend suite | Not green: the production process adapter uses POSIX selector pipes and other tests assume POSIX process/filesystem behavior. The frontend harness has its own bounded Windows transport that still runs the real verifier. Do not report this as a passed full backend suite or Linux CI |

The actual browser scenarios cover:

1. Session exchange, Secure/HttpOnly/SameSite cookies, restoration after reload and logout.
2. Merchant invoice/case creation, backend listing pagination and state filtering.
3. Customer consent default, evidence file upload, response-loss retry with one stored evidence record, claim submission, acknowledgement-only behavior and denied merchant navigation/API reads.
4. Real valid receipt recovery with 100,000 candidate zatoshis and zero offline credit; tampered, missing receipt and missing transaction inputs without credit.
5. Merchant stale-version rejection, explicit renewed review and response-loss retry of a noncredit decision with one resolution.
6. One-time grant code behavior, lost-code replay without redisclosure and revocation.
7. Reviewer section/evidence selection; private claim omission; original receipt byte preservation; denied writes and report-only export; actual revocation returning to login.
8. Reviewer scoped and merchant full-history packet downloads; source receipt bytes preserved; the downloaded merchant packet reproduces through the actual replay engine.
9. Keyboard focus, mobile width and axe checks for login, invoice, customer, merchant case, grant and reviewer views; ignored query codes and stripped fragments on an already-open Connect page.
10. Missing-CSRF recovery through another session and local eight-hour expiry using the browser's controlled clock.
11. Separate, visibly simulated approval response-loss retry yielding one 100,000-zatoshi credit, a partially paid case, and an opaque cross-invoice duplicate-output finding.

The reproduction procedure, environment variables and platform limits are in [apps/web/README.md](../apps/web/README.md). Private synthetic credentials, encryption keys, TLS keys and automatic browser artifacts are excluded from the branch and handoff.

## Integration and remaining release gates

[PR #26](https://github.com/Kurisu-Labs/zecsolve/pull/26) merged on October 12,
2026 as `8e8843dce410aaed30e10d960af5de2c857e0edd`, including P4's recorded
browser evidence above. Its foundation, web and container checks passed; those
checks did not yet execute Playwright.

Person 3's [browser CI and deployment integration](browser-ci.md) merged in
PR #28: it repeats the eight offline scenarios through the actual packaged nginx
ingress, runs the simulated scenario separately, and retains sanitized evidence. Both Linux CI compositions passed at `7d4ffcf`;
see E-07/E-08 in the [release evidence index](release-evidence.md). This consumes
P4’s suite and does not transfer UI ownership. M3.1 live evidence merged in PR #27. Operator deployment, reviewed UI
screenshots, retention/deletion for private-customer use and the assembled final
release evidence remain the separate [release handoffs](release-evidence.md#remaining-handoffs-and-release-decision).

The original local evidence above is preserved as recorded; it is not relabeled
as a Linux CI or public-deployment run. No public deployment or real customer
operation is established by this handoff.
