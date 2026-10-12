# Trusted chain observations

M3 adds an optional read-only Zebra RPC adapter. **No endpoint was available for live validation.** Tests use explicitly synthetic HTTP responses plus the real historical receipt verifier. They demonstrate the adapter and transaction behavior, not live inclusion or a tested node deployment.

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

Zebra's wire names and optional mempool/side-chain fields were checked against its published [transaction serialization source](https://zebra.zfnd.org/internal/src/zebra_rpc/methods/types/transaction.rs.html) and [RPC response source](https://zebra.zfnd.org/internal/src/zebra_rpc/methods.rs.html), plus the [header response contract](https://zebra.zfnd.org/internal/zebra_rpc/methods/struct.BlockHeaderObject.html). The actual configured node's response format/version still needs integration testing. Nodes missing required fields fail closed.

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

## Pending live gate

Once an endpoint exists, use the public fixture workflow to create an invoice/case/evidence and run the real verifier. Refresh via the route above, inspect the returned node version, chain/binding/header facts, and then approve through the normal merchant resolution route. Record the exact app revision, time, node version, supported methods, sanitized observation, and decision IDs. Never save credentials or a credential-bearing endpoint in the trace.

Until that real observation and approval trace exists, keep the M3 live gate and release credit path marked incomplete. Customer/reviewer grants, disclosure consent, browser sessions and authorized replay packets are merged. Person 4’s initial frontend is partial; remaining M6 integration/acceptance retains its explicit-resumption gate. See the [release evidence index](release-evidence.md) for current proof and outstanding handoffs.
