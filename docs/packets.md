# CasePacketV1 contract

`contracts/case-packet.schema.json` is generated from
`zecsolve.schemas.packet.CasePacketV1`. Packet v1 carries a typed payload and an
integrity manifest. Its interpretation is local and offline; no field is an
instruction to fetch a URL, install a historical version or execute a command.

The payload contains the authorized report, original evidence components,
provenance, declared implementations, and (for the merchant) the current balance
allocation context. The existing merchant report supplies the immutable invoice,
policy, case, assertions, initial and decision-time evaluations, observations,
approved allocations, decisions/approvers and event history. It is preserved in
its historical record formats, not rebuilt as newly hashed historical records.
The current balance context is captured at the same snapshot as the report.

`FULL_HISTORY` means the packet includes the case's recorded historical inputs;
it does not promise valid evidence, fresh chain confirmation, trusted authorship
or truth of business assertions. `NOT_SUBMITTED` records an originally missing
component; `OMITTED` records withheld data. A reviewer packet always uses the M4.5
projection and `LIMITED`, with explicit omission reasons and no hidden record
counts or identifiers. Reviewer submission payloads and balance allocation
context are withheld even when every report section was selected. Foreign
allocation conflicts are opaque external assertions, never foreign invoice or
merchant details. All packets declare the four external assertion limits.

## Exact bytes and hash profile

| Field/hash | Covered bytes |
| --- | --- |
| Component `data` | Canonical base64 of the original UTF-8 bytes; no trimming, Unicode normalization, JSON reformatting or hex case change |
| Component `sha256` | SHA-256 of those original bytes, after base64 decoding |
| `decoded_transaction_sha256` | SHA-256 of decoded transaction bytes using the historical hex decoder; null for missing/undecodable input |
| Submission payload | Exact canonical JSON bytes encrypted by the writer; merchant only; hash matches evidence `payload_sha256` |
| Integrity `payload_sha256` | SHA-256 of canonical JSON of the entire `payload`, excluding the envelope and integrity manifest |
| Invoice snapshot hash | Original v1 invoice representation, excluding `created_at` and `snapshot_hash` |
| Evaluation snapshot hash | Original snapshot representation, excluding `snapshot_hash` |
| Event hashes | Existing payload hash plus historical event header, excluding `event_id`, `payload`, `event_hash`; preserve chain order/previous hash |

`zecsolve-json-v1` is the existing project profile: recursively sorted string
keys, compact separators, UTF-8 with unescaped Unicode, integers/booleans/null,
arrays and objects, no floats or nonfinite values. It is not a claim to implement
RFC 8785. Serialization outside the payload may use ordinary pretty JSON.
Consumers check the hash of the supplied payload *before* schema defaults or
normalization. Duplicate JSON keys, noncanonical base64, invalid UTF-8 and packets
over 64 MiB are rejected. Component decoding is bounded at 4.2 MB. Empty bytes
remain PRESENT with SHA-256 of the empty string; null is NOT_SUBMITTED with no
hash. A newline in the original hex file changes its original-file hash without
changing the decoded-transaction hash.

The implementation declarations identify the verifier name/version, result
schema and Glasspane revision, and all rules versions used. A missing version is
explicitly null; an unknown implementation is data for a consumer to reject or
report unsupported. It never authorizes executable selection. Initial rules
0.1.0 and decision rules 0.2.0 remain separate; decision snapshots record the
original evaluation clock and source-authority assertion.

SHA-256 detects changes relative to the supplied hashes. An attacker who rewrites
a packet and all its hashes has not been authenticated by this format. Chain
observations, grant/consent provenance, approved allocations and merchant claims
remain external assertions. Offline transaction recovery cannot freshly prove
inclusion, confirmations or the absence of conflicting allocations.

## Fixtures and checks

[Public/synthetic fixtures](../fixtures/packets/README.md) cover legacy/current
submission and observation formats, complete history and scoped disclosure.
`test_packet_contract.py` checks lossless representations, original versus decoded
hashes, preserved historical hashes, scope invariants and ambiguous encodings.
M5.0 freezes this contract only; M5.1 adds local replay and M5.2 adds authorized
snapshot export.

## Offline replay (M5.1)

After `make setup`, use the installed command:

```sh
uv run --locked replay-case fixtures/packets/complete-v1.json
uv run --locked replay-case /path/to/authorized-packet.json --verifier target/debug/zecsolve-verifier
```

`python -m zecsolve.replay` is equivalent. The packet path is a local file, never
a URL. The trusted verifier path comes only from the operator's `--verifier`
argument or `ZECSOLVE_VERIFIER_PATH`; packet strings never select commands,
programs, imports, downloads or network destinations. No database is opened and
no credit is changed. The normal bounded verifier adapter enforces per-run input,
output and timeout limits; the packet file read is capped at 64 MiB.

The JSON response (`case-replay-v1`) contains independent checks for packet and
historical integrity, real cryptographic recovery, rules/arithmetic, and missing
or external context. Dispatch recognizes only the locally implemented verifier
0.1.0 / result schema 1 / pinned Glasspane revision and rules 0.1.0 (initial) and
0.2.0 (decision). Decision arithmetic uses the recorded clock and source-authority
assertion; it does not freshly authorize the source or refresh the chain.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | REPRODUCED | Included full history reproduces; business/chain assertions remain external |
| 1 | FAILED | File, contract, integrity, relationship, recovery or arithmetic mismatch |
| 2 | LIMITED | Scoped omissions, missing version metadata/inputs, unavailable local verifier or historical runtime failure prevent full replay |
| 3 | UNSUPPORTED | A declared historical implementation is not locally supported |

A negative receipt result may reproduce as `NEGATIVE_RESULT_REPRODUCED`; that is
not successful output recovery. A self-consistent rewritten packet can pass its
hash checks and still fail real recovery or arithmetic. Conversely, self-consistent
business assertions are not authenticated just because replay succeeds.

`fixtures/packets/replay-results.json` records actual CLI outputs and exact input
file SHA-256 values for valid, one-byte tampered, scoped, missing-version and
unsupported-version examples. Regenerate them using
`uv run python scripts/record_replay_examples.py`; all inputs are deterministic
variants of the public/synthetic fixtures. This file contains results, not packets.

## Authorized export (M5.2)

`GET /api/cases/{case_id}/export` returns `CasePacketV1` with
`Cache-Control: no-store` and an attachment filename containing only the case UUID.
Use the normal merchant bearer credential or HTTPS browser session. Customers
receive 403; inaccessible merchant/case IDs receive 404. Reviewers need their
grant's explicit `allow_export` in addition to the selected report/evidence scope.
A report-only grant does not authorize export. A case-only export grant produces
an explicitly limited packet with no original evidence.

The service reuses M4.5's explicit projection and P1's persisted authorization;
selected evidence still requires processing and reviewer-sharing consent. Evidence
selection authorizes exact original components even if the `evidence` report
section was not selected. A reviewer packet never adds private linked claims,
complete submission payloads, actor identities, full audit payloads, historical
allocation inputs or arbitrary RPC dictionaries. Original receipts themselves
are sensitive and remain lossless; previously downloaded copies cannot be revoked.

One PostgreSQL repeatable-read transaction captures the report, current allocation
context, evidence metadata and ciphertext. Decryption runs outside the transaction,
using only the captured bytes. A fresh authorization transaction then revalidates
the merchant credential/browser session or grant, its expiry/revocation and the
entire evidence consent selection before returning the packet. Approval committed
during export cannot mix old events with new balances or allocation inputs.
A captured older consistent snapshot may be returned; export is not a claim to
contain writes committed after that snapshot began.

Oversized packets fail with `413 EXPORT_TOO_LARGE`; ciphertext-size budgeting
precedes decryption and the final serialized packet is bounded at 64 MiB. Missing
content/history and invalid stored integrity fail closed. Concurrent database
serialization/lock conflicts return the existing retryable 409 boundary. The
operation writes no credit, decisions or events and requires no idempotency key.

The database/HTTP suite `test_exports.py` covers the five-role matrix, exact v2
claim/evidence replay, legacy history with simulated approval, concurrent approval,
opaque foreign conflicts, grant/credential/session revocation, expiry, private
claim linkage, report-only and case-only export scope, size limits, tampering,
and originally missing versus empty components. These are public/synthetic tests;
live chain validation and P4's actual browser/download integration remain separate.
