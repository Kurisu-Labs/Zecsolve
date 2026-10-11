"""Bounded read-only Zebra RPC. Provider assertions remain separate from receipt proof."""

import hashlib
import ipaddress
import json
import re
import time
from datetime import UTC, datetime

import httpx

from zecsolve.adapters.chain import unavailable_observation

MAX_RESPONSE_BYTES = 4_200_000
HASH = re.compile(r"[0-9a-f]{64}\Z")


class RpcFailure(Exception):
    pass


def integer(value, minimum=0):
    if type(value) is not int or not minimum <= value <= 2147483647:
        raise RpcFailure("RPC_MALFORMED_RESPONSE")
    return value


def hash_value(value):
    if not isinstance(value, str) or not HASH.fullmatch(value):
        raise RpcFailure("RPC_MALFORMED_RESPONSE")
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RpcFailure("RPC_MALFORMED_RESPONSE")
        result[key] = value
    return result


def validate_endpoint(endpoint, allow_private_http):
    try:
        url = httpx.URL(endpoint)
        if not url.host or url.username or url.password or url.query or url.fragment:
            raise ValueError
        if url.scheme == "https":
            return
        address = ipaddress.ip_address(url.host)
        private = address.is_loopback or any(
            address in ipaddress.ip_network(subnet)
            for subnet in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7")
        )
        if url.scheme == "http" and allow_private_http and private:
            return
    except (ValueError, httpx.InvalidURL):
        pass
    raise ValueError("RPC requires HTTPS or explicitly allowed private/loopback IP HTTP")


class ZebraObserver:
    def __init__(self, settings, *, transport=None):
        self.endpoint = settings.rpc_url.get_secret_value()
        validate_endpoint(self.endpoint, settings.rpc_allow_private_http)
        self.source = settings.rpc_source_id
        self.timeout = settings.rpc_timeout_seconds
        self.tip_max_age = settings.rpc_tip_max_age_seconds
        self.auth = (
            (settings.rpc_username.get_secret_value(), settings.rpc_password.get_secret_value())
            if settings.rpc_username.get_secret_value()
            else None
        )
        self.transport = transport

    def authorizes(self, observation):
        return (
            observation.schema_version == "decision-observation-v2"
            and observation.source_kind == "RPC"
            and observation.source == self.source
        )

    def _call(self, client, method, params, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RpcFailure("RPC_TIMEOUT")
        with client.stream(
            "POST",
            self.endpoint,
            json={"jsonrpc": "2.0", "id": method, "method": method, "params": params},
            timeout=remaining,
        ) as response:
            if response.status_code in (401, 403):
                raise RpcFailure("RPC_AUTH_FAILED")
            if response.status_code != 200:
                raise RpcFailure("RPC_HTTP_FAILED")
            if response.headers.get("content-encoding", "identity") != "identity":
                raise RpcFailure("RPC_UNSUPPORTED_ENCODING")
            body = bytearray()
            for chunk in response.iter_bytes():
                if time.monotonic() > deadline:
                    raise RpcFailure("RPC_TIMEOUT")
                if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                    raise RpcFailure("RPC_RESPONSE_TOO_LARGE")
                body.extend(chunk)
        data = json.loads(body, object_pairs_hook=unique_object)
        if not isinstance(data, dict) or data.get("id") != method:
            raise RpcFailure("RPC_MALFORMED_RESPONSE")
        if data.get("error") is not None:
            raise RpcFailure("RPC_LOOKUP_FAILED" if method == "getrawtransaction" else "RPC_ERROR")
        result = data.get("result")
        if not isinstance(result, dict):
            raise RpcFailure("RPC_MALFORMED_RESPONSE")
        return result

    def _chain(self, data):
        if data.get("chain") != "main":
            raise RpcFailure("RPC_NETWORK_MISMATCH")
        blocks = integer(data.get("blocks"))
        headers = integer(data.get("headers"))
        estimate = integer(data.get("estimatedheight"))
        progress = data.get("verificationprogress")
        if type(progress) not in (int, float) or not 0.999 <= progress <= 1:
            raise RpcFailure("RPC_UNSYNCED")
        if headers != blocks or estimate > blocks + 2:
            raise RpcFailure("RPC_UNSYNCED")
        if "initialblockdownload" in data and data["initialblockdownload"] is not False:
            raise RpcFailure("RPC_UNSYNCED")
        return {
            "chain": "main",
            "blocks": blocks,
            "headers": headers,
            "estimatedheight": estimate,
            "bestblockhash": hash_value(data.get("bestblockhash")),
            "synced": True,
        }

    def observe(self, network, txid, expected_raw_tx_sha256):
        result = unavailable_observation(network, txid, expected_raw_tx_sha256)
        result.update(
            schema_version="decision-observation-v2", source_kind="RPC", source=self.source, rpc={}
        )
        # Start time makes time spent querying count against the policy freshness budget.
        deadline = time.monotonic() + self.timeout
        try:
            if network != "mainnet" or not txid or not expected_raw_tx_sha256:
                raise RpcFailure("RPC_MISSING_BINDING")
            hash_value(txid)
            hash_value(expected_raw_tx_sha256)
            with httpx.Client(
                transport=self.transport,
                auth=self.auth,
                follow_redirects=False,
                trust_env=False,
                headers={"Accept-Encoding": "identity"},
            ) as client:

                def call(method, params=None):
                    return self._call(client, method, params or [], deadline)

                version = call("getnetworkinfo")
                node_version = integer(version.get("version"))
                subversion = version.get("subversion")
                if not isinstance(subversion, str) or not re.fullmatch(
                    r"[\w./:+() -]{1,120}", subversion
                ):
                    raise RpcFailure("RPC_MALFORMED_RESPONSE")
                result["rpc"]["node"] = {"version": node_version, "subversion": subversion}
                chain = self._chain(call("getblockchaininfo"))
                result["rpc"]["chain"] = chain
                tip = call("getblockheader", [chain["bestblockhash"], True])
                tip_time = integer(tip.get("time"))
                if (
                    hash_value(tip.get("hash")) != chain["bestblockhash"]
                    or integer(tip.get("height")) != chain["blocks"]
                    or integer(tip.get("confirmations")) != 1
                ):
                    raise RpcFailure("RPC_INCONSISTENT_CHAIN")
                if not -120 <= datetime.now(UTC).timestamp() - tip_time <= self.tip_max_age:
                    raise RpcFailure("RPC_STALE_TIP")
                result["rpc"]["tip_time"] = tip_time
                tx = call("getrawtransaction", [txid, 1])
                raw = tx.get("hex")
                if not isinstance(raw, str) or not re.fullmatch(r"(?:[0-9a-fA-F]{2})+", raw):
                    raise RpcFailure("RPC_MALFORMED_RESPONSE")
                if (
                    hash_value(tx.get("txid")) != txid
                    or hashlib.sha256(bytes.fromhex(raw)).hexdigest() != expected_raw_tx_sha256
                ):
                    raise RpcFailure("RPC_TRANSACTION_MISMATCH")
                count = (
                    integer(tx["confirmations"], -1)
                    if tx.get("confirmations") is not None
                    else None
                )
                height = integer(tx["height"], -1) if tx.get("height") is not None else None
                active = tx.get("in_active_chain")
                if active is not None and type(active) is not bool:
                    raise RpcFailure("RPC_MALFORMED_RESPONSE")
                block = hash_value(tx["blockhash"]) if tx.get("blockhash") is not None else None
                result["rpc"]["transaction"] = {
                    "txid": txid,
                    "raw_tx_sha256": expected_raw_tx_sha256,
                    "confirmations": count,
                    "height": height,
                    "in_active_chain": active,
                    "blockhash": block,
                }
                if block is None and height is None and count is None and active is not True:
                    result.update(state="UNCONFIRMED", reason_code="RPC_MEMPOOL", confirmations=0)
                else:
                    block = hash_value(block)
                    header = call("getblockheader", [block, True])
                    block_height = integer(header.get("height"))
                    block_count = integer(header.get("confirmations"), -1)
                    if hash_value(header.get("hash")) != block or (
                        height != -1 and block_height != height
                    ):
                        raise RpcFailure("RPC_INCONSISTENT_CHAIN")
                    result["rpc"]["block"] = {
                        "hash": block,
                        "height": block_height,
                        "confirmations": block_count,
                    }
                    if block_count == -1 and count == 0 and height == -1 and active is not True:
                        result.update(
                            state="UNCONFIRMED",
                            reason_code="RPC_SIDE_CHAIN",
                            block_hash=block,
                            block_height=block_height,
                            confirmations=0,
                        )
                    elif (
                        block_count >= 1
                        and count == block_count
                        and height is not None
                        and active is not False
                        and block_count == chain["blocks"] - height + 1
                    ):
                        result.update(
                            state="CONFIRMED",
                            reason_code="RPC_BEST_CHAIN",
                            block_hash=block,
                            block_height=height,
                            confirmations=block_count,
                        )
                    else:
                        raise RpcFailure("RPC_INCONSISTENT_CHAIN")
                final_chain = self._chain(call("getblockchaininfo"))
                if (final_chain["blocks"], final_chain["bestblockhash"]) != (
                    chain["blocks"],
                    chain["bestblockhash"],
                ):
                    raise RpcFailure("RPC_CHAIN_CHANGED")
        except RpcFailure as error:
            result.update(
                state="UNAVAILABLE",
                reason_code=str(error),
                confirmations=None,
                block_hash=None,
                block_height=None,
            )
        except httpx.TimeoutException:
            result.update(state="UNAVAILABLE", reason_code="RPC_TIMEOUT")
        except httpx.HTTPError:
            result.update(state="UNAVAILABLE", reason_code="RPC_TRANSPORT_FAILED")
        except (ValueError, TypeError, RecursionError):
            result.update(state="UNAVAILABLE", reason_code="RPC_MALFORMED_RESPONSE")
        if result["state"] == "UNAVAILABLE":
            result.update(confirmations=None, block_hash=None, block_height=None)
        return result
