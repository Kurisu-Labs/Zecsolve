# Public and synthetic packet fixtures

Generated deterministically by `uv run python scripts/build_packet_fixtures.py`
with the real bundled Rust verifier. No database, RPC endpoint, customer data,
wallet-wide key or live confirmation is involved.

- `complete-v1.json`: public Glasspane receipt/transaction, synthetic invoice,
  legacy v1 evidence/event, initial offline rules 0.1.0, a **SIMULATED** observation
  and synthetic approval evaluated by rules 0.2.0.
- `complete-v2.json`: the same public inputs and synthetic case with current v2
  consent/evidence/event representation. An additional v2 RPC-shaped observation
  is explicitly `UNAVAILABLE`, labeled `synthetic-unavailable-not-live`, and
  carries no fabricated node response or confirmation.
- `scoped.json`: consented evidence and verification projection from the current
  synthetic fixture. It omits submission metadata, full audit and historical
  allocation context and is explicitly `LIMITED`.

The original file provenance, MIT license and upstream pinned revision are in
[the input manifest](../manifest.json). Fixture IDs are UUIDv5 values under an
`example.invalid` synthetic namespace; case/consent/approval/clock values are
fictional. The simulated 100,000-zatoshi allocation is not a live-chain or
merchant-payment assertion. Source strings and invoice/decision history are
untrusted business assertions, even when every integrity check passes.

Regeneration preserves all historical invoice/evaluation/event hash algorithms.
See [the packet contract](../../docs/packets.md) for hash bases and privacy limits.
