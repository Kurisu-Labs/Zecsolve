"""No network source is configured for M2; production confirmation stays unavailable."""

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
    # Future deployments must explicitly compose an authenticated source policy.
    return False
