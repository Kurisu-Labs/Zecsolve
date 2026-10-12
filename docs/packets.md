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
