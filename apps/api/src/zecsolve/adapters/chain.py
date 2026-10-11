"""Offline fallback; deployments explicitly compose their trusted RPC source."""

from datetime import UTC, datetime


def unavailable_observation(network, txid, raw_hash, reason="NO_CHAIN_OBSERVER"):
    return {
        "state": "UNAVAILABLE",
        "source_kind": "OFFLINE",
        "source": "offline",
        "reason_code": reason,
        "observed_at": datetime.now(UTC),
        "network": network,
        "txid": txid,
        "raw_tx_sha256": raw_hash,
    }


class OfflineObserver:
    def observe(self, network, txid, expected_raw_tx_sha256):
        return unavailable_observation(network, txid, expected_raw_tx_sha256)


def no_trusted_source(observation):
    # No source is implicitly authorized.
    return False
