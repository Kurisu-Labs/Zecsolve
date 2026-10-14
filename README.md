# zecsolve

**Resolve disputed Zcash shielded payments without asking customers to expose their wallet history.**

zecsolve is a case-management app for merchants and payment-support teams handling missing, partial, or disputed payments. A customer can share a receipt for one shielded output; the merchant can check it against an invoice, review chain evidence, and record a decision. Authorized reviewers can inspect the case and replay its evidence offline.

[Try the demo](https://zecsolve.vercel.app) · [Developer setup](docs/getting-started.md) · [Product specification](docs/PRD.md)

## How it works

1. **Open a case.** The merchant records the invoice amount, recipient, and matching terms.
2. **Collect selected evidence.** The customer submits a claim and, when available, an output-specific receipt and raw transaction. The disclosure explains which amount, recipient, and memo will be revealed.
3. **Verify and compare.** The Rust verifier recovers the selected output. The app checks invoice matching, payment amounts, prior allocations, and separately obtained chain observations.
4. **Make a decision.** The merchant can request more evidence, reject it, or approve eligible invoice credit. The same output cannot be credited to another invoice in the system.
5. **Share a reviewable record.** Case-scoped access controls what a reviewer can see. Authorized JSON exports preserve evidence and decision history for offline replay.

Receipt validity, chain confirmation, and merchant approval answer different questions. A valid receipt alone does not prove payer identity or authorize credit. **Approving a case records invoice credit; it does not transfer ZEC.**

## Try it

Open [the hosted app](https://zecsolve.vercel.app/connect) and choose **Use demo data** to explore public fixture examples without an access code. This browser mode replays recorded results and simulates decisions; it does not run live backend verification or credit a real payment.

Authenticated merchant, customer, and reviewer workflows use the deployed API and require a privately provisioned access code. The [deployment record](docs/vercel-deployment.md) documents the historical-receipt checks, live RPC observation, approval, and export/replay results.

### Example: a partial payment

The bundled example uses a real historical Orchard receipt for **0.001 ZEC** and a synthetic invoice for **0.002 ZEC**. One ZEC equals 100,000,000 zatoshis.

| Stage | Candidate amount | Credited | Outstanding |
|---|---|---|---|
| Receipt recovered, before approval | 0.001 ZEC | 0 ZEC | 0.002 ZEC |
| After an eligible merchant approval | 0 ZEC | 0.001 ZEC | 0.001 ZEC |

Before approval, the candidate suggests a 0.001 ZEC shortfall but does not reduce the outstanding balance. The offline proof of concept stops at this stage; approval requires a trusted chain observation. No new payment is sent in this example.

## Built with

| Component | Technology and responsibility |
|---|---|
| Web app | Vue 3, TypeScript, and Tailwind CSS for merchant, customer, and reviewer workflows |
| API and storage | FastAPI and PostgreSQL for cases, scoped access, encrypted original evidence, decisions, and allocation records |
| Receipt verification | Rust wrapper around pinned Glasspane libraries for output recovery and recipient normalization |
| Chain observations | Read-only Zebra-compatible RPC, configured by the operator |
| Replay | Python CLI that checks exported evidence, integrity, and historical rules without a database or network |

The hosted demo serves the frontend and API together on Vercel with Neon PostgreSQL. A separate Docker Compose deployment is also available. See [the codebase guide](TEAM_GUIDE.md) for the source map.

## Current limits

- **Demonstration scope:** the app is demonstrated with public historical evidence and synthetic invoices. Production operating controls and retention/deletion procedures for private customer data remain unfinished; see [security boundaries](docs/security.md) and [deployment limits](docs/vercel-deployment.md#remaining-operating-gates).
- **Receipt compatibility:** the verifier accepts mainnet receipt format v0 with v5 transactions from NU5 through NU6.2. Orchard has a real historical fixture; the Sapling recovery path lacks an end-to-end historical fixture here. Ironwood compatibility is not established.
- **Evidence availability:** customers need a compatible output receipt for cryptographic recovery. A claim without one can be recorded, but it is not a verified payment. Previously shared receipt copies cannot be recalled.
- **Limits of proof:** offline recovery and replay cannot establish fresh chain inclusion. The application holds no funds, requires no spending or wallet-wide viewing keys, and does not issue refunds. Test results are not a security audit.

## Run the proof of concept

Requires Rust/Cargo **1.99+**, Python **3.12+**, [uv](https://docs.astral.sh/uv/), a C compiler/linker, and make. Run from the repository root:

```sh
make setup
make poc
```

The first setup downloads locked dependencies. The proof of concept then runs offline without PostgreSQL: the valid receipt recovers 100,000 zatoshis, the tampered receipt fails, chain status stays `UNAVAILABLE`, and credited value stays zero.

For API/database setup, merchant credentials, frontend development, direct verifier commands, and packet replay, follow [Getting started](docs/getting-started.md).

## Documentation

- [Product specification](docs/PRD.md): users, requirements, and intended behavior.
- [Getting started](docs/getting-started.md): local setup, API entry points, and verification commands.
- [Packet export and replay](docs/packets.md): format, disclosure limits, and replay outcomes.
- [Hosted deployment](docs/vercel-deployment.md) and [Docker deployment](docs/deployment.md): configuration and operating procedures.
- [Release evidence](docs/release-evidence.md): recorded checks and remaining release requirements.
- [Contributing](CONTRIBUTING.md): development workflow and validation requirements.

## Attribution

Built by Kurisu Labs. Cryptographic receipt recovery uses [Glasspane](https://github.com/dolepee/glasspane) `gp-core` and `gp-types`, pinned at `f6468e6d08a7adad53bf2991a311358dc84e869b`, with its [MIT license](third_party/glasspane/LICENSE) retained. [Fixture provenance](fixtures/manifest.json) records the original receipt and transaction sources and hashes. zecsolve adds the case workflow, scoped access and consent, merchant decisions, duplicate-credit protection, and export/replay layer.
