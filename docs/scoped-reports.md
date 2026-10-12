# Reviewer disclosure (M4.5)

`GET /api/cases/{id}/report` keeps the existing merchant response. A reviewer
browser session receives `reviewer-report-v1`, assembled from explicit fields in
its grant's `report_sections`. Unselected sections are absent in HTTP JSON;
nullable fields *inside* a selected section remain null. Case detail and listing
remain merchant-only. Customers cannot read reports or evidence.

| Section | Reviewer content |
| --- | --- |
| case | State, version and creation time |
| invoice | Terms and policy, without merchant/policy/invoice identifiers |
| claims | Text, reported transaction, time and claim ID, only with explicit claim sharing consent; labeled assertions |
| evidence | Selected, consented metadata and original-component hashes |
| verifications | Results for selected, consented evidence only |
| observations | Typed projected historical observations for those verifications, including OFFLINE/SIMULATED/RPC source; no arbitrary RPC dictionaries |
| evaluations | Initial historical findings/arithmetic, without nested invoice/allocation/actor snapshots |
| balances | Current invoice aggregate and selected candidate findings; foreign conflicts are opaque findings |
| decisions | Reason/action/time/amount for selected verifications, plus case-level noncredit decisions; no actor or nested snapshots |
| events | ID/action/time for records disclosed by the other selected sections; no actors, payloads or hash chain |

A section grant is an explicit disclosure decision: `invoice` includes recipient
and expected memo, `balances` includes case-level approved totals, and `decisions`
includes the merchant's free-text reason. Render claim/reason/source strings as
text, not HTML. Linking shared evidence to a private claim does **not** share the
claim. Legacy evidence without explicit sharing consent cannot be selected.

`GET /api/cases/{id}/evidence/{evidence_id}` returns `reviewer-evidence-v1` for
reviewers. `GET .../evidence/{evidence_id}/content` returns `evidence-content-v1`
for authorized merchants/reviewers: evidence ID and exact `receipt_json` and
`raw_tx_hex` strings only. Whitespace, UTF-8 text, null and empty strings are
preserved. Neither endpoint reveals encryption material, consent/grant IDs,
linked private claims or complete submission payloads. Original receipt content
can itself be sensitive; grant selection and submission consent authorize those
original components without redaction.

Both reads reuse P1's `authorize_case_access`, selection and consent rules.
Reports use one repeatable-read transaction. Evidence decryption happens outside
the transaction and rechecks permission afterward; grant/session/credential
revocation and expiry therefore still apply. A report grant alone cannot read
original evidence. Export remains a distinct permission, implemented by M5.2.

These are limited projections, not a complete historical audit or replay packet.
Omission metadata does not reveal counts or IDs of hidden evidence. Historical
observations do not establish fresh chain inclusion. The merchant response and
all historical snapshot/event hashes retain their original contracts.

The generated schemas are in `contracts/reviewer-report.schema.json`,
`contracts/reviewer-evidence.schema.json` and `contracts/evidence-content.schema.json`.
`apps/api/tests/test_reviewer_reports.py` exercises five roles, section and claim
consent, exact original content, unselected/guessed IDs, opaque foreign conflicts,
selected decision history, revocation during decryption and expired grants.
