# M7.1 backend deployment preparation

This increment supplies a bounded TLS deployment for the current backend and Person 4's built Vue application. It is preparation for M7.1, not completion of that milestone: M4.2 browser sessions, cookie/Origin/CSRF acceptance, and Person 4's actual-backend browser acceptance remain integration gates. Live RPC validation and release/restore rehearsal remain separate M3.1/M7.2 work.

The existing `compose.yaml`, `make api`, and development POC retain their behavior. Use the separate [deployment Compose file](../infra/compose.deployment.yaml) and the `deployment` target in [Dockerfile.api](../infra/Dockerfile.api) for this composition. It runs `python -m zecsolve.deployment`, which applies forward migrations and starts one bounded Uvicorn process. Application/authentication services are reused without introducing another identity or permission model.

## Layout and limits

Only the unprivileged nginx ingress publishes ports. It terminates TLS, redirects HTTP to the configured HTTPS hostname/port, and proxies `/api`, `/health`, and the frontend to FastAPI. The API and database have no published host ports. A separate internal network isolates database traffic; the API retains outbound connectivity for an operator-configured trusted RPC source.

| Control | Deployment behavior |
|---|---|
| TLS | Operator-supplied certificate and private key; TLS 1.2/1.3, HSTS, no session tickets |
| Public host | Explicit `ZECSOLVE_DEPLOY_HOST`; arbitrary Host headers are rejected by the backend |
| Forwarded headers | nginx replaces client values; Uvicorn trusts only the configured ingress IP, never every caller |
| API rate/connection limits | 5 requests/second per source IP, burst 10, at most 10 simultaneous API connections per IP; rejection is 429 |
| Request bodies | 4,200,000 bytes at ingress and in the existing API, including chunked requests |
| Time bounds | 10-second client header/body timeouts, 3-second upstream connect, 60-second upstream read; existing bounded verifier/RPC calls remain authoritative |
| API capacity | One process, 32 concurrent connections/tasks, existing two verifier slots; 2 CPUs, 1 GiB memory, 128 PIDs |
| Ingress capacity | 0.5 CPU, 128 MiB memory, 32 PIDs; bounded connection/rate zones |
| Database capacity | 1 CPU, 512 MiB memory, 128 PIDs; durable named data volume |
| Filesystem/privileges | API and ingress run non-root with read-only roots, dropped capabilities, no new privileges, and 128 MiB `/tmp` tmpfs |
| Public POC/docs | Deployment entry point always returns 404, even if a POC token was configured |
| Readiness | Existing packaged migration-head, verifier and evidence-key checks; a missing frontend build prevents startup |
| Logs | No access logs or raw nginx error logs; API runtime events omit messages/arguments/tracebacks; migration output is suppressed; container logs rotate at 10 MiB × 3 |

Limits are a starting deployment budget, not a throughput claim. Multiple users behind one NAT share the ingress rate bucket. Do not add another proxy/CDN without revisiting client-IP trust and rate-limit tests. Change the edge subnet and both fixed addresses together if they overlap an existing network. A database outage makes readiness fail while process liveness remains available. Chain-source availability remains separate: an RPC outage cannot be presented as an invalid receipt or silently grant approval.

## Operator configuration

Use Docker Engine with BuildKit and Docker Compose v2 or newer. Keep all secret files **outside the build context** in a private directory (mode 0700). File-backed Compose secrets must be readable by their non-root container consumers; Compose bind mounts do not reliably remap host file ownership. The smoke harness uses files readable within a private parent directory. Use your host/orchestrator's secret storage and permissions for a real deployment.

| File in the secrets directory | Contents |
|---|---|
| `database_password` | Random PostgreSQL password for this deployment |
| `database_url` | Matching SQLAlchemy URL, e.g. `postgresql+psycopg://zecsolve:<URL-encoded-password>@db:5432/zecsolve` |
| `evidence_key` | Base64 of 32 random bytes; preserve it securely with its key ID across restarts and restores |
| `rpc_url`, `rpc_username`, `rpc_password` | Existing trusted-source settings; create empty files to keep the observer offline |
| `tls_certificate` | PEM certificate chain valid for the configured hostname |
| `tls_key` | Matching PEM private key |

The app reads mounted secret files through the existing settings model. Secrets are not Docker build arguments or CLI arguments. Do not print `docker compose config` with unrelated sensitive environment overrides, attach raw diagnostics to a PR, or commit secret files. The image build excludes `.env` files, caches, local frontend dependencies, and existing frontend output.

Set public deployment coordinates in the shell (values below are placeholders):

```sh
export ZECSOLVE_DEPLOY_HOST=zecsolve.example.com
export ZECSOLVE_DEPLOY_SECRETS_DIR=/absolute/private/zecsolve-secrets
export ZECSOLVE_EVIDENCE_KEY_ID=deployment-v1
# Default listeners are loopback 8080/8443. Change deliberately for your ingress host.
export ZECSOLVE_DEPLOY_BIND=127.0.0.1
export ZECSOLVE_DEPLOY_HTTP_PORT=8080
export ZECSOLVE_DEPLOY_HTTPS_PORT=8443
docker compose -f infra/compose.deployment.yaml up --build -d --wait
```

For a public host, provision DNS/certificates and firewall rules first, then explicitly choose the bind address and usually ports 80/443. Certificate issuance/renewal and public infrastructure provisioning are operator tasks; this preparation does not create them. Reload/recreate ingress after certificate rotation. Keep the API port private. The loopback defaults are useful for rehearsal and do not constitute a public deployment.

The API applies migrations before serving; migration failure exits nonzero with a generic runtime error. Deploy one API instance for this P0 composition. A normal stop preserves the database volume:

```sh
docker compose -f infra/compose.deployment.yaml down
```

Do not use `down --volumes` on data you intend to keep. Existing evidence-key, retention/deletion, encrypted backup and restore obligations remain; PostgreSQL files are not encrypted by this Compose file. Filesystem/volume encryption belongs to the deployment host. Real customer use remains gated by the security and release plan.

## Frontend and session handoff

The image executes Person 4's existing locked `npm ci` and `npm run build`, then copies `apps/web/dist` to `/app/web`. Frontend source, dependencies and build configuration stay with Person 4. FastAPI serves built assets and falls back to `index.html` for HTML browser routes. Missing API/health/assets, dotfiles and escaping symlinks do not receive the SPA fallback. Responses are non-cacheable and use security headers; the current CSP allows same-origin scripts/connections/fonts and inline styles required by the current app.

P1's M4.2 must supply the browser session contract and any additional secret/configuration mapping. Rehearse `Secure`, `HttpOnly`, `SameSite`, cookie scope, exact Origin/CSRF checks, expiry/revocation and logout through this actual TLS ingress after M4.2 merges. The ingress must not manufacture identity or weaken those checks. P4 must exercise merchant/customer/reviewer screens against that backend and confirm CSP compatibility, keyboard use and responsive behavior. Serving the current build and fetching its assets do not complete those browser tests.

## Reproduce the container checks

From the repository root, with a running Docker daemon, Python 3.12+ and OpenSSL:

```sh
python3 scripts/check_deployment.py
```

The harness creates a unique Compose project, random test-only credentials, a short-lived localhost certificate, private host files, and a disposable database. It builds the actual images and validates the certificate using an explicit trust anchor, not disabled TLS verification. It checks frontend/assets and API routing, POC disablement, fixed/chunked body limits, rate limiting with spoofed forwarded headers, actual Docker resource/privilege settings, readiness under a database stop/restart, and absence of secret canaries in logs. On completion it removes only its own containers, networks, data volume and temporary files. A sanitized result is saved in `.cache/deployment-result.json`.

`--keep-on-failure` retains the unique test project and private diagnostics for local repair; use the reported `coordinates.json` to recover its project name and nonsecret settings, then remove only that project. Do not share the retained directory: it also holds disposable secrets. The [deployment workflow](../.github/workflows/deployment.yml) runs the same actual-container checks in CI. Configuration parsing alone is not acceptance evidence.

Local results and the remaining M7.1 gate are recorded in [DEVELOPMENT.md](DEVELOPMENT.md). General application changes still require `make test`, `make lint`, and the relevant PostgreSQL suite under [CONTRIBUTING.md](../CONTRIBUTING.md).

Implementation references: [nginx request limiting](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html), [Compose service controls](https://docs.docker.com/reference/compose-file/services/).
