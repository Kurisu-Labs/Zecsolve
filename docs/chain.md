# Trusted chain observations

M3 adds an optional read-only Zebra RPC adapter. **M3.1 live validation passed on October 12, 2026**, using the operator-selected QuickNode public demo endpoint and the existing public historical receipt. The [recorded run](#recorded-live-run) includes a fresh RPC-backed merchant approval and retry; the evidence merged in PR #27. Unit/database RPC tests continue to use explicitly synthetic HTTP responses and do not themselves establish live inclusion. No deployed-node or full-release acceptance is claimed.

## Configure a trusted source

Apply migration `0008` using `make migrate`. An empty `ZECSOLVE_RPC_URL` retains the offline observer and blocks credit. Set these privately in `.env` or the deployment environment:

| Setting | Default / constraint |
|---|---|
| `ZECSOLVE_RPC_URL` | Empty; HTTPS endpoint without URL userinfo, query, or fragment |
| `ZECSOLVE_RPC_SOURCE_ID` | `trusted-zebra`; stable public label, never a credential |
| `ZECSOLVE_RPC_USERNAME`, `ZECSOLVE_RPC_PASSWORD` | Optional HTTP Basic credentials, represented as secrets |
| `ZECSOLVE_RPC_ALLOW_PRIVATE_HTTP` | `false`; enabling permits HTTP only for loopback, RFC1918 IPv4, or unique-local IPv6 literals |
| `ZECSOLVE_RPC_TIMEOUT_SECONDS` | 10, maximum 30; shared lookup budget with bounded HTTP operation timeouts |
| `ZECSOLVE_RPC_TIP_MAX_AGE_SECONDS` | 900, configurable from 75 to 3600 |

Plain HTTP DNS names and link-local metadata addresses are rejected. Use HTTPS for a named private service. Compose forwards these settings; inside a container, loopback refers to that container. Use a distinct source ID when switching providers so historical provenance remains meaningful. No client request can select an endpoint, supply RPC credentials, or assert confirmations. The app never uses a simulated observer through configuration.

The endpoint must support `getnetworkinfo`, `getblockchaininfo`, verbose `getrawtransaction`, and verbose `getblockheader`. Redirects and environment proxies are disabled. Each response is capped at 4,200,000 bytes; compressed responses are rejected. Failures return diagnostic reason codes without upstream error text, URLs, or credentials. A lookup only discloses transaction IDs and block hashes; receipts, OCKs, memos, and receiver values stay local.

## Observation checks

The adapter binds the returned `txid` and SHA-256 of decoded transaction bytes to the already verified transaction. It requires mainnet, validated header/block agreement, estimated height no more than two ahead, verification progress at least 0.999, and a recent best-block timestamp. The tip freshness allowance is an engineering limit, not proof that a provider is honest or that the network cannot reorganize.

It checks the containing header's hash, height, and best-chain confirmation count against the transaction and tip height, then rereads chain info. A moving tip during the lookup produces `UNAVAILABLE / RPC_CHAIN_CHANGED`; retry with a new key. Header confirmation counts are trusted provider assertions, not locally verified consensus proofs.

| Observed condition | Result |
|---|---|
| Bound transaction on a stable best chain | `CONFIRMED`; policy separately requires sufficient confirmations and freshness |
| Bound mempool transaction | `UNCONFIRMED / RPC_MEMPOOL` |
| Bound side-chain transaction/header | `UNCONFIRMED / RPC_SIDE_CHAIN` |
| Timeout, auth/HTTP failure, lookup error, malformed/inconsistent response, unsynced/stale tip, wrong network or bytes | `UNAVAILABLE` with a diagnostic code; receipt result is unchanged |

Zebra's wire names and optional mempool/side-chain fields were checked against its published [transaction serialization source](https://zebra.zfnd.org/internal/src/zebra_rpc/methods/types/transaction.rs.html) and [RPC response source](https://zebra.zfnd.org/internal/src/zebra_rpc/methods.rs.html), plus the [header response contract](https://zebra.zfnd.org/internal/zebra_rpc/methods/struct.BlockHeaderObject.html). The operator-selected node passed the [recorded M3.1 integration](#recorded-live-run); other configured endpoints still require compatibility validation. Nodes missing required fields fail closed.

`decision-observation-v2` preserves selected integer/string/bool/null provenance: advertised node version/subversion, chain/tip data, transaction binding, and containing-header facts. It excludes raw transaction content and unrelated RPC fields. Observation time is captured before network work, so lookup time counts against the invoice's existing 60-second freshness policy. Older observation-v1 records and decision hashes remain unchanged.

## Refresh and decide

Send an authenticated merchant request with a new `Idempotency-Key`:

```http
POST /api/cases/CASE_UUID/chain-observations
Authorization: Bearer MERCHANT_TOKEN
Idempotency-Key: refresh-001
Content-Type: application/json

{"verification_id":"VERIFICATION_UUID"}
```

The initial response is 201. A completed same-credential/case/key request returns the original observation with 200 and `Idempotency-Replayed: true`; changing its verification returns 409. A fresh key performs a fresh lookup. Unknown request fields return 422, absent/revoked credentials 401, and inaccessible verifications 404. Reauthorization occurs after network work and lock waits. Concurrent same-key requests can perform two read-only lookups but commit one observation/retry record. A refresh stores diagnostics without changing the case version or creating a business decision.

Each new `APPROVE_OUTPUT` still performs its own refresh; a manual refresh is never substituted for that check. A failed refresh cannot reuse a prior confirmation. Receipt recovery remains independently recorded. Reports include initial offline observations, decision/refresh observations, historical decisions, and current approved balances.

A later observation of an approved transaction in the mempool/side chain adds `chain_review: [{code: "APPROVED_OUTPUT_CHAIN_REVIEW", resolution_id, observation_id}]`. It blocks additional credit in that case. An unavailable lookup does not erase an already observed loss of inclusion. A later confirmed observation from that source meeting the original invoice’s confirmation threshold clears the inclusion warning; new credit still undergoes its own policy evaluation. Original allocations and decision snapshots remain intact, including completed retries. This is on-demand review, not a background chain monitor or automatic reversal.

<a id="pending-live-gate"></a>

## Live validation evidence

The live gate requires the public fixture workflow to create an invoice/case/evidence and run the real verifier, followed by a refresh and approval through the normal merchant resolution route. Evidence must identify the actual node version, chain/binding/header facts, exact app revision, time and decision IDs. Never save credentials or a credential-bearing endpoint in the trace.

### Recorded live run

The unchanged [JSON evidence](evidence/m3-live-f8a594f.json) was produced from clean
revision `f8a594fa7364a47fd94d961054b1f88429195b90` on **2026-10-12
13:23:24.163901–13:23:30.760930 UTC**. Runtime application code matches the
`4066ec8` main baseline; the added harness/procedure are committed in `f8a594f`.
Environment: Darwin 27.0.0 arm64, Python 3.12.14, PostgreSQL 17.11 (Homebrew),
Rust 1.99.0; migrations through `0009`. Fixture hashes and verifier binary hash
are in the artifact. Its SHA-256 is
`c7e9c885978313878a97c31a6c986f26339d9d8768b77ac27845e29d0486c2b1`.

| Check | Actual result |
|---|---|
| Source / advertised node | `quicknode-public-demo`; `/Zebra:6.4.2/`, numeric version `6040200` |
| Methods exercised | `getnetworkinfo`, `getblockchaininfo`, verbose `getrawtransaction`, verbose `getblockheader` |
| Receipt and transaction binding | `VALID`, 100,000 zatoshis; txid `66167cd3020eb329446e86d80ccd0494baa3959bf9a0e586dbdccd204b6dcfd0`; decoded raw SHA-256 `bd616384a2268a293f0de81a9b3b713badba39803d637be48df3e3d4a504c943` |
| Live inclusion | `CONFIRMED / RPC_BEST_CHAIN`; block `3361512`, hash `0000000000e48f1302b6293a705708816f2a36817c08561fcbb3ed822e064551`; 153,734 confirmations at tip `3515245` |
| Source synchronization | Mainnet; blocks/headers/estimated height agree, adapter verification-progress and fresh-tip checks passed; stable tip across each lookup |
| Authorization and freshness | Anonymous refresh `401`; authenticated refresh `201`; approval source authorized; separate approval observation age **2.600470 seconds**, below the 60-second policy limit; confirmations exceed the required 10 |
| Merchant decision | `APPROVE_OUTPUT` returned `201`; resolution `3dfad984-1cf8-446a-9eeb-25db004291b2`, approval observation `539e4bf9-e506-472e-8954-33059243f14d`; case/invoice/evidence/verification/evaluation/output references retained in JSON |
| Balances and retries | 0 credited before approval; 100,000 credited and 100,000 outstanding afterwards; refresh and approval retries returned identical records with `200 / Idempotency-Replayed: true`; exactly one decision |
| Isolation | Fresh synthetic invoice, ephemeral merchant/encryption key, random disposable DB schema; schema removal verified; no payment sent |

The case remains `UNDER_REVIEW` because this was a partial payment against a
synthetic 200,000-zatoshi invoice. The report's balance projection still contains
`CHAIN_UNVERIFIED` from the initial offline verification and `ALREADY_ALLOCATED`
for that candidate; these do not erase the separate successful decision snapshot
and persisted credit. Inspect `approval.evaluation.observation` and
`approval.evaluation.result` for the actual live decision, rather than interpreting
the offline projection as a new RPC lookup.

This is a time-specific provider observation, not locally verified consensus or a
promise of continued inclusion, provider availability, or production readiness.
Existing synthetic reorganization/outage tests remain separate; those failure
conditions were not induced on the public node. Full M7 still requires its
frontend, deployed-target and team evidence. No live result was fabricated or
substituted into the offline fixture manifest or historical development entries.

### Repeatable live validation procedure

The opt-in [validation harness](../scripts/validate_live_chain.py) exercises the
normal authenticated FastAPI routes in process using `TestClient`; its configured
`ZebraObserver` makes actual HTTPS requests. It does not replace the observer,
source authority, verifier or RPC transport. This is backend/API validation,
not browser, TLS ingress or deployed-container acceptance.

1. Start from a clean, committed revision and build the matching verifier with
   `make build`. Run from the repository root with the development dependencies
   installed (`uv sync --locked`).
2. Set `ZECSOLVE_TEST_DATABASE_URL` privately to a **disposable PostgreSQL** database
   whose role can create/drop schemas. The harness creates a random isolated
   schema, applies all migrations, and removes that schema in `finally`; it does
   not use the ordinary application's database URL. Do not use a production DB.
3. Configure the operator-selected endpoint in `.env` using the settings above.
   For this task the operator selected QuickNode's public documentation endpoint,
   `https://docs-demo.zec-mainnet.quiknode.pro/`, source label
   `quicknode-public-demo`, HTTPS, no Basic authentication, a 30-second lookup
   budget and the existing 900-second tip age limit. QuickNode publishes this URL
   in its [RPC examples](https://www.quicknode.com/docs/zcash/getnetworkinfo).
   This choice is for the public-fixture validation; continued availability and
   quotas are not established. Configure an operator-managed endpoint for ongoing
   deployment and record new evidence when the source or runtime changes.
4. Run once, choosing a new evidence filename:

   ```sh
   uv run --locked python scripts/validate_live_chain.py --output /tmp/m3-live-validation.json
   ```

The run verifies the fixture manifest hashes, provisions an ephemeral merchant
credential and encryption key, creates a synthetic 200,000-zatoshi invoice and
case, submits encrypted public evidence, and recovers the real 100,000-zatoshi
output. Initial verification stays offline and credits zero. Anonymous refresh
is denied. Authenticated refresh must bind the actual transaction bytes to
mainnet block/confirmation data. A same-key refresh returns the identical result.
Approval must perform a **different, fresh RPC observation**, satisfy the invoice's
10-confirmation/60-second policy, and allocate exactly 100,000 zatoshis. Retrying
approval must return the identical decision and leave exactly one decision,
100,000 credited and 100,000 outstanding.

No wallet or new payment is needed. The only source evidence is the already-public
Glasspane fixture. Saved JSON contains revision/time/environment, verifier binary
and fixture hashes, selected public observation facts, synthetic invoice/decision
data, sanitized HTTP steps and schema cleanup status. It excludes the RPC URL,
authentication headers, merchant token, encryption key and database URL. Review
the output before committing it. A failed assertion produces no successful
evidence file; a moving chain tip or provider outage can require a separate fresh
run. Never overwrite a historical run or treat a failed lookup as a live pass.

This command is deliberately absent from CI: the offline suites and container
rehearsal must not acquire a dependency on the shared public RPC service.

The M3.1 acceptance run and evidence merged in PR #27. Customer/reviewer grants, disclosure consent, browser sessions and authorized replay packets are merged. Person 4 owns frontend acceptance, separately from this API run. See the [release evidence index](release-evidence.md) for current proof and outstanding handoffs.
