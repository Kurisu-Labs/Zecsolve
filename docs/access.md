# Shared case access foundation

M4.0 supplies persistence and transaction-time authorization for M4.1 grants, M4.2 browser sessions, M4.4 customer submissions, and M4.5 scoped reports. It does not by itself expose customer/reviewer routes. Existing merchant bearer routes and historical invoice/evidence/verification/decision hashes stay compatible.

## Actor and permission contract

- `MerchantPrincipal(merchant_id, credential_id, session_id=None)` retains the existing credential identity. A later browser session does not replace its underlying credential.
- `GrantPrincipal(merchant_id, case_id, grant_id, role, session_id=None)` represents a customer or reviewer of one case. It never needs a fake merchant credential.
- `authorize_case_access(session, principal, case_id, permission, evidence_id=None)` returns server-derived `AccessContextV1`. Call it inside the same transaction as the protected read/write, and again after external work or lock waits before returning/committing. Contexts are not bearer capabilities and must never be trusted when supplied by clients.
- `authorize_merchant` remains the gate for invoice management, verification, decisions, grant management, and merchant reports. It rejects grant principals even when they belong to the same merchant.

| Actor | Permission vocabulary |
|---|---|
| Merchant | `case:summary`, `case:manage`, `claim:submit`, `evidence:submit`, `report:read`, `evidence:read`, `case:export`, `case:verify`, `case:resolve` |
| Customer | `case:summary`, `claim:submit`, `evidence:submit`, confined to its grant's case |
| Reviewer | `report:read`; optional selected `evidence:read` and explicit `case:export` |

Reviewer `report_sections` is an explicit selection of `case`, `invoice`, `claims`, `evidence`, `verifications`, `observations`, `evaluations`, `balances`, `decisions`, and `events`. At least one section is required. Customer scope forbids report sections, evidence selections, and export. A reviewer scope's evidence IDs are also stored as scoped foreign-key rows; mismatches fail closed. Original-evidence read/export additionally requires a processing/sharing consent record. Public-fixture labels and old merchant processing acknowledgements do not grant reviewer consent.

**Person 2 must implement explicit projections.** Authorization to read a report never means returning the full merchant report. Use the returned section/evidence selections and avoid foreign allocation details; report-contained derived fields remain disclosures. No reviewer report route or exporter is enabled by this foundation.

## Persistence handoff

Migration `0009` adds:

- `case_grants`: owner/case/issuer, customer/reviewer role, hashed token, immutable scope/expiry, revocation time.
- `grant_evidence`: exact evidence allowlist constrained to the same case and merchant.
- `grant_creation_requests`: merchant/credential/case/key/body-hash to grant reference; no plaintext access code.
- `browser_sessions`: hashed token and CSRF value, exactly one underlying credential or scoped grant, expiry of at most eight hours, and revocation. Service issuance must additionally cap expiry to the underlying access expiry.
- `evidence_consents`: immutable evidence/case/owner, credential or grant actor, disclosure version, processing authorization, and reviewer-sharing choice. M4.4 writes this atomically with evidence/audit/retry; do not infer consent for historical evidence.
- `access_submission_requests`: credential-or-grant actor, case, claim/evidence operation, key/hash, resource, and event references for future M4.4 writers.

Claims gain nullable `merchant_id`, `actor_credential_id`, and `actor_grant_id`; evidence gains nullable `actor_grant_id` while retaining the existing `submitted_by` credential field. New attribution requires a merchant context and cannot specify both actor types. Existing rows remain unchanged. Person 3 must use a new supported workflow payload/version for customer attribution, preserve exact encrypted content, and retain legacy merchant readers; no new submission writer is included here.

Grant/session records permit only irreversible revocation, not deletion or changes to token, scope, expiry, or identity. Consent/selection/retry records reject edits/deletes. Fresh credentials/grants/sessions get separate rows. These controls are not protection against a database administrator rewriting schema or records.

## Rechecks and migration safety

Acquire the underlying credential/grant shared lock before any session lock, then evaluate the database clock. Re-read identity/revocation fields from the locked rows rather than cached ORM state. A session cannot bypass expired/revoked underlying access; mismatched session linkage is rejected. Existing merchant workflow lock ordering remains credential → session (if present) → invoice → case.

Downgrade locks authorizers and new tables before checking history, and refuses to remove any populated access/consent/retry or attributed records. Empty access rollback preserves existing merchant ciphertext and metadata. Use forward migrations for accepted history and stop traffic before planned rollback.

Published contracts: [access context](../contracts/access-context.schema.json) and [grant scope](../contracts/grant-scope.schema.json). The next Person 1 increment exposes grant creation/metadata/revocation, followed by secure browser code exchange and Origin/CSRF-protected sessions. Customer submission and reviewer projections remain owned by their assigned contributors.
