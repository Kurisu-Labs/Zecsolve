import hashlib
import json
import uuid
from datetime import UTC, datetime

import httpx
import pytest
from zecsolve.adapters.rpc import MAX_RESPONSE_BYTES, ZebraObserver, validate_endpoint
from zecsolve.config import Settings
from zecsolve.domain.snapshots import canonical_bytes
from zecsolve.schemas.resolution import observation_adapter

TXID = "ab" * 32
BLOCK = "cd" * 32
TIP = "ef" * 32
RAW = "010203"
RAW_HASH = hashlib.sha256(bytes.fromhex(RAW)).hexdigest()


class Node:
    """Synthetic wire responses based on Zebra serde fields; not live validation."""

    def __init__(self, txid=TXID, raw=RAW):
        self.requests = []
        self.chain = dict(
            chain="main",
            blocks=109,
            headers=109,
            estimatedheight=109,
            verificationprogress=1.0,
            bestblockhash=TIP,
        )
        self.tip = dict(
            hash=TIP, height=109, confirmations=1, time=int(datetime.now(UTC).timestamp())
        )
        self.tx = dict(
            txid=txid, hex=raw, blockhash=BLOCK, height=100, confirmations=10, in_active_chain=True
        )
        self.block = dict(hash=BLOCK, height=100, confirmations=10)
        self.failure = None

    def handle(self, request):
        data = json.loads(request.content)
        self.requests.append(data)
        if self.failure:
            return self.failure(request, data)
        result = {
            "getnetworkinfo": dict(version=3000000, subversion="/Zebra:test/"),
            "getblockchaininfo": self.chain,
            "getrawtransaction": self.tx,
            "getblockheader": self.tip if data["params"] == [TIP, True] else self.block,
        }[data["method"]]
        return httpx.Response(
            200, content=json.dumps({"jsonrpc": "2.0", "id": data["id"], "result": result})
        )

    def observer(self, **settings):
        return ZebraObserver(
            Settings(_env_file=None, rpc_url="https://node.invalid", **settings),
            transport=httpx.MockTransport(self.handle),
        )


def observe(node):
    data = node.observer().observe("mainnet", TXID, RAW_HASH)
    return observation_adapter.validate_python(
        data | {"observation_id": uuid.uuid4(), "verification_id": uuid.uuid4()}
    )


def test_confirmed_binding_and_sanitized_versioned_provenance():
    node = Node()
    node.tx["private_unneeded_field"] = "must-not-persist"
    result = observe(node)
    assert result.state == "CONFIRMED" and result.confirmations == 10
    assert result.block_hash == BLOCK and result.block_height == 100
    assert result.rpc["node"]["subversion"] == "/Zebra:test/"
    assert "must-not-persist" not in result.model_dump_json()
    assert "hex" not in result.rpc["transaction"]
    canonical_bytes(result.model_dump(mode="json"))
    assert all(
        item["method"]
        in {"getnetworkinfo", "getblockchaininfo", "getblockheader", "getrawtransaction"}
        for item in node.requests
    )
    assert next(x for x in node.requests if x["method"] == "getrawtransaction")["params"] == [
        TXID,
        1,
    ]
    assert node.observer().authorizes(result)
    assert not node.observer(rpc_source_id="other").authorizes(result)


@pytest.mark.parametrize(
    "target,changes,reason",
    [
        ("chain", {"chain": "test"}, "RPC_NETWORK_MISMATCH"),
        ("chain", {"estimatedheight": 130}, "RPC_UNSYNCED"),
        ("chain", {"headers": 110}, "RPC_UNSYNCED"),
        ("chain", {"verificationprogress": 0.9}, "RPC_UNSYNCED"),
        ("chain", {"verificationprogress": float("nan")}, "RPC_UNSYNCED"),
        ("chain", {"blocks": True}, "RPC_MALFORMED_RESPONSE"),
        ("tip", {"time": 1}, "RPC_STALE_TIP"),
        ("tip", {"hash": BLOCK}, "RPC_INCONSISTENT_CHAIN"),
        ("tx", {"txid": TIP}, "RPC_TRANSACTION_MISMATCH"),
        ("tx", {"hex": "040506"}, "RPC_TRANSACTION_MISMATCH"),
        ("tx", {"hex": "01 zz"}, "RPC_MALFORMED_RESPONSE"),
        ("tx", {"confirmations": "10"}, "RPC_MALFORMED_RESPONSE"),
        ("tx", {"height": None}, "RPC_INCONSISTENT_CHAIN"),
        ("tx", {"in_active_chain": False}, "RPC_INCONSISTENT_CHAIN"),
        ("block", {"hash": TIP}, "RPC_INCONSISTENT_CHAIN"),
        ("block", {"height": 101}, "RPC_INCONSISTENT_CHAIN"),
        ("block", {"confirmations": 9}, "RPC_INCONSISTENT_CHAIN"),
    ],
)
def test_bad_or_ambiguous_source_fails_closed(target, changes, reason):
    node = Node()
    getattr(node, target).update(changes)
    result = observe(node)
    assert result.state == "UNAVAILABLE" and result.reason_code == reason


def test_mempool_and_side_chain_are_not_invalid_receipts():
    node = Node()
    node.tx = dict(txid=TXID, hex=RAW)
    result = observe(node)
    assert result.state == "UNCONFIRMED" and result.reason_code == "RPC_MEMPOOL"
    node.tx.update(blockhash=BLOCK, height=-1, confirmations=0, in_active_chain=False)
    node.block["confirmations"] = -1
    result = observe(node)
    assert result.state == "UNCONFIRMED" and result.reason_code == "RPC_SIDE_CHAIN"
    assert result.block_height == 100


@pytest.mark.parametrize(
    "status,reason",
    [
        (401, "RPC_AUTH_FAILED"),
        (403, "RPC_AUTH_FAILED"),
        (302, "RPC_HTTP_FAILED"),
        (503, "RPC_HTTP_FAILED"),
    ],
)
def test_http_failures_are_sanitized(status, reason):
    node = Node()
    node.failure = lambda *_: httpx.Response(status, text="secret credentials")
    result = observe(node)
    assert result.reason_code == reason and "secret" not in result.model_dump_json()
    assert len(node.requests) == 1


def test_timeout_and_missing_transaction():
    node = Node()

    def timeout(*args):
        raise httpx.ReadTimeout("secret endpoint")

    node.failure = timeout
    assert observe(node).reason_code == "RPC_TIMEOUT"
    original = node.handle

    def missing(request):
        data = json.loads(request.content)
        if data["method"] == "getrawtransaction":
            return httpx.Response(
                200, json={"id": data["id"], "error": {"code": -5, "message": "secret"}}
            )
        return original(request)

    node.failure = None
    node.handle = missing
    assert observe(node).reason_code == "RPC_LOOKUP_FAILED"


@pytest.mark.parametrize(
    "content,reason",
    [
        (b"x" * (MAX_RESPONSE_BYTES + 1), "RPC_RESPONSE_TOO_LARGE"),
        (b"not json", "RPC_MALFORMED_RESPONSE"),
        (b'{"id":"wrong","result":{}}', "RPC_MALFORMED_RESPONSE"),
    ],
)
def test_bounded_malformed_responses(content, reason):
    node = Node()
    node.failure = lambda *_: httpx.Response(200, content=content)
    assert observe(node).reason_code == reason


def test_chain_change_during_lookup_is_unavailable():
    node = Node()
    original = node.handle

    def changing(request):
        data = json.loads(request.content)
        if data["method"] == "getblockchaininfo" and len(node.requests) > 2:
            node.chain["bestblockhash"] = BLOCK
        return original(request)

    node.handle = changing
    assert observe(node).reason_code == "RPC_CHAIN_CHANGED"


@pytest.mark.parametrize(
    "url,allow,valid",
    [
        ("https://node.example/rpc", False, True),
        ("http://127.0.0.1:8232", True, True),
        ("http://[::1]:8232", True, True),
        ("http://192.168.1.1:8232", True, True),
        ("http://127.0.0.1", False, False),
        ("http://8.8.8.8", True, False),
        ("http://localhost", True, False),
        ("http://169.254.169.254", True, False),
        ("https://user:password@node.example", False, False),
        ("https://node.example?token=secret", False, False),
    ],
)
def test_endpoint_configuration(url, allow, valid):
    if valid:
        validate_endpoint(url, allow)
    else:
        with pytest.raises(ValueError):
            validate_endpoint(url, allow)


def test_missing_binding_does_not_call_provider():
    node = Node()
    assert node.observer().observe("mainnet", None, None)["reason_code"] == "RPC_MISSING_BINDING"
    assert not node.requests


def test_asgi_composition_is_offline_by_default_and_never_trusts_simulation():
    from zecsolve.adapters.chain import OfflineObserver
    from zecsolve.main import create_app

    offline = create_app(Settings(_env_file=None))
    assert isinstance(offline.state.chain_observer, OfflineObserver)
    assert not offline.state.chain_authority(None)
    app = create_app(Settings(_env_file=None, rpc_url="https://node.invalid"))
    assert isinstance(app.state.chain_observer, ZebraObserver)
    observation = observe(Node())
    assert app.state.chain_authority(observation)
    assert not app.state.chain_authority(
        observation.model_copy(update={"source_kind": "SIMULATED"})
    )
    app.state.engine.dispose()
    offline.state.engine.dispose()


def test_duplicate_json_fields_are_not_accepted():
    node = Node()
    node.failure = lambda *_: httpx.Response(
        200, content=b'{"id":"getnetworkinfo","id":"getnetworkinfo","result":{}}'
    )
    assert observe(node).reason_code == "RPC_MALFORMED_RESPONSE"
