# Case grant lifecycle

M4.1 lets an authenticated merchant create and revoke customer/reviewer access for one owned case. Apply migrations through `0009`; the grant code is intended for M4.2 browser-session exchange, not for merchant bearer routes. Customer submissions and reviewer report projections remain M4.4/M4.5 work.

| Route | Request/result |
|---|---|
| `POST /api/cases/{id}/grants` | Merchant credential and `Idempotency-Key`; returns grant metadata and the initial access code after commit |
| `GET /api/cases/{id}/grants` | Merchant-only metadata list, newest first; includes expired/revoked records, never access codes |
| `DELETE /api/cases/{id}/grants/{grant_id}` | Merchant-only, idempotent revocation; returns metadata with the original revocation timestamp |

A customer grant request is `{"scope":{"role":"customer"},"ttl_hours":24}`. Its only permissions are case summary and claim/evidence submission within that case. It cannot request report sections, evidence reads, export, verification, approval, or grant management.

A reviewer request may use `{"scope":{"role":"reviewer","report_sections":["case","balances"],"evidence_ids":[],"allow_export":false},"ttl_hours":24}`. Report sections are explicit; at least one is required. Evidence IDs and export permission are additional selections. Evidence must belong to the same case and have an immutable processing/sharing consent record. An old source label or merchant processing acknowledgement does not authorize reviewer sharing. Report-only grants work without evidence consent; M4.4 will supply the consent writer.

Lifetime defaults to 24 hours and is restricted to integer values from 1 through 168 hours. These are engineering defaults, not a claim of completed retention policy. Scope and expiry cannot be edited: revoke and issue a new grant for different permissions.

## Secret and retry behavior

New creation returns 201 and a `zsg_` access code containing 256 random bits. The database stores only its SHA-256 digest. The code is excluded from object representations, metadata, retry rows, and audit payloads. It is disclosed only after successful commit.

Same merchant/credential/case/key/body returns 200 with the original grant metadata and `access_code=null`; no replacement secret is generated. Changed bodies conflict with 409. Concurrent equal requests create one grant and only the winning request receives its code. A lost creation response means the secret cannot be recovered: revoke that grant and create another using a new key. Store and transfer the initial code privately; do not put it in URLs, logs, or shared repository files.

Grant creation does not change the case's payment state/version or allocate credit. Revoking a merchant credential stops that credential and its sessions, but does not automatically revoke independently issued case grants. Revoke those grants explicitly when required. Grant expiry/revocation invalidates its future authorization and any derived sessions; it cannot erase evidence copies already downloaded elsewhere.

## Checks and handoff

Absent/invalid merchant credentials return 401; inaccessible cases/grants/evidence return 404; missing sharing consent or a nonmerchant actor returns 403; malformed scope/lifetime/key returns 422; changed retry bodies and bounded lock conflicts return 409; database failures return generic 503. All responses use `Cache-Control: no-store`.

Creation holds the credential lock, then the owned case lock to serialize retry keys, and rechecks credential validity after waits and before commit. Grant/selection/retry rows commit together. Revoke locks the owned grant and preserves the first revocation time. Existing immutable/revoke-only database controls remain active.

Person 1 next supplies secure browser sessions. Person 2 must enforce [access.md](access.md) section/evidence/export selections in explicit projections; a grant does not make the existing merchant report publicly readable. Person 3 supplies scoped customer submission and consent. This increment exposes no customer/reviewer data routes and no frontend changes.

Published schemas: [create request](../contracts/grant-create-request.schema.json), [creation result](../contracts/grant-created.schema.json), and [metadata list](../contracts/grant-list.schema.json).
