# Customer claims and evidence (M4.4)

Merchants and case-scoped customers can submit claims and encrypted evidence. A customer uses P1's [browser session](sessions.md) with the configured HTTPS Origin and session-bound `X-CSRF-Token`; a grant access code is exchanged at `/api/session`, never used as a merchant bearer token. Merchant bearer and cookie clients remain supported. Reviewer sessions cannot submit.

Submission records an authenticated actor's assertion of permission, not independent proof of identity, payment, or authority to share. Nothing here verifies evidence, approves a case, or allocates credit automatically. Customers cannot read case details, listings, reports, evidence metadata/content, or invoke merchant verification/decision/grant operations.

## Claims

`POST /api/cases/{case_id}/claims`, with `Idempotency-Key`:

```json
{
  "reported_txid": null,
  "note": "I have a receipt but the merchant has not credited this invoice.",
  "disclosure_version": "claim-disclosure-v1",
  "processing_authorized": true,
  "share_with_reviewers": false
}
```

At least one of a reported transaction ID or nonblank note is required. Transaction IDs must be 64 lowercase hex characters; they remain unverified assertions and cause no network fetching. Notes are at most 4,096 UTF-8 bytes, reject NUL, and remain untrusted plain text. Person 4 must render them as text, never HTML. Claim notes/transaction IDs are stored in the existing claim columns outside the encrypted evidence blob; database/backups and retention requirements still apply.

Present this disclosure before submitting `claim-disclosure-v1`:

> I am authorized to submit this transaction ID and note for processing in this merchant case. The merchant can read them. Reviewer sharing is a separate choice and is off by default. Copies already shared cannot be recalled. My claim does not prove payment.

Processing must be the explicit boolean `true`; sharing must be a boolean and defaults to `false`. The version is required. The server derives merchant, case, actor, role and acceptance time. A merchant submission records the merchant's assertion; it must not be described as consent obtained directly from a customer.

## Encrypted evidence v2

`POST /api/cases/{case_id}/evidence`, with `Idempotency-Key`:

```json
{
  "receipt_json": "{\"example\":\"opaque contents, not a server path\"}\n",
  "raw_tx_hex": null,
  "source": "Customer-supplied receipt",
  "source_kind": "customer_submission",
  "claim_id": null,
  "disclosure_version": "evidence-disclosure-v2",
  "processing_authorized": true,
  "share_with_reviewers": false
}
```

Present this disclosure before submitting `evidence-disclosure-v2`:

> I am authorized to submit these selected payment details for processing in this merchant case. The merchant can read them. A receipt can disclose its selected amount, recipient and memo. Reviewer sharing is a separate choice and is off by default. Copies already shared cannot be recalled. Submission does not prove payment.

The explicit v2 disclosure is required for customer uploads. Receipt/raw transaction components remain optional, opaque and byte-preserving, including whitespace, empty strings and missing components. Existing UTF-8/component/request limits and AES-GCM encryption remain in force. Metadata version 2 uses the existing version-1 encryption envelope/associated-data format; original ciphertext is never rewritten.

`claim_id` is an optional link to an attributed claim in the same case and merchant. Customers can link only claims from their own grant; merchants can link any attributed claim in their case. Unknown, foreign or another customer's claim IDs return 404. Evidence sharing does not authorize sharing a linked claim's note.

`source_kind` accepts `customer_submission` (default), `merchant_submission` and `public_fixture`. These labels are unverified caller assertions. They never override the server-derived credential/grant attribution or imply consent.

Both claims and v2 evidence return only `SubmissionAcknowledgementV1`: `schema_version`, `status: "accepted"`, `operation`, `submission_id`, and UTC `accepted_at`. `submission_id` is the claim/evidence UUID. No case state/version, balances, other submissions, grants, consent records, hashes or evidence content are disclosed. There is no Location header advertising an inaccessible read route. Responses are `Cache-Control: no-store`.

## Retries, transactions and access failures

A new submission returns 201. The same actor, case, operation, key and body return 200 with the identical acknowledgement and `Idempotency-Replayed: true`; changed bodies return 409. Parent credential/grant identity scopes retries, so a renewed session can recover a lost response. A new grant or credential has its own namespace. Claims and evidence have separate operation namespaces. Merchant evidence v1/v2 share the same logical retry namespace: changing the version cannot reuse a key to create a second upload.

The case write serializes in credential/grant → session → invoice → case order. Claim/evidence, consent, attribution, retry reference, case version/state and audit event commit together; failures roll back everything. Encryption runs outside database locks under the existing bounded capacity, and authorization is rechecked before committing. Expiry after lock waits and revocation during encryption reject the write. Completed retries still require current authorization, including on terminal cases; terminal cases reject new writes.

Every accepted claim increments the case version without changing state. Evidence follows the existing OPEN/AWAITING_EVIDENCE/UNDER_REVIEW behavior; these states say nothing about validity. Unknown input/server-owned fields and invalid keys return sanitized 422 responses. Missing/expired/revoked access returns 401, disallowed actions/Origin/CSRF return 403, foreign objects return 404, retry/history/terminal conflicts return 409, oversized payloads return 413, busy crypto returns 429, and key/database failures return 503. A lock conflict may return a retryable 409. No access secrets or original evidence belong in error messages.

## Persistence and downstream handoff

This uses migration `0009`; no additional schema or authorization model is introduced.

- Claims retain server-derived `merchant_id`, `actor_credential_id` or `actor_grant_id`, and `claimant_role`. Their immutable schema-2 `CLAIM_SUBMITTED` event records disclosure version, processing/sharing choices, server time and a hash of the complete request. It contains no note/transaction text. `access_submission_requests` links the claim, actor and event.
- Evidence v2 records either `submitted_by` (credential) or `actor_grant_id`, never both, plus a schema-2 metadata record. Its `evidence_consents` row captures the actor, disclosure version, choices and time. Metadata and the schema-2 `EVIDENCE_SUBMITTED` event bind the consent and optional claim references. The access retry row binds evidence and event.
- Person 2 must consume these consent records and attribution explicitly in M4.5/M5. Selected evidence requires its processing/sharing consent; legacy merchant acknowledgement alone is insufficient. Claim disclosure choices are in the linked immutable claim event; a report-section grant must not silently convert a false choice to consent. Linking a claim to shareable evidence does not change the claim's choice. Neither submission receipt is proof of payment.
- Merchant metadata, verification and report readers support both evidence versions and mixed schema-1/schema-2 audit histories. Attributed claim text/actor/time must match the recorded request hash and event before a merchant report is returned; mismatches fail with 409. Existing merchant request/metadata/event v1 bytes, hashes, retries and responses remain unchanged. Only v2 submissions create the new sharing-consent row; there is no consent backfill.
- Person 4 owns disclosure display/checkboxes, cookie handling, retry recovery and text rendering. The acknowledgement is the complete customer response; do not follow it with merchant case/report/evidence reads. Actual browser acceptance remains M6 work.

Contracts: [claim request](../contracts/claim-submit-request.schema.json), [evidence v2 request](../contracts/evidence-submit-request-v2.schema.json), [acknowledgement](../contracts/submission-acknowledgement.schema.json), [merchant evidence v2 metadata](../contracts/evidence-stored-v2.schema.json), and [submission event v2](../contracts/submission-event-v2.schema.json).
