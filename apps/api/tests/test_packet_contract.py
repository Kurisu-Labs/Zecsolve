import hashlib
import json

import pytest
from pydantic import ValidationError
from zecsolve.domain.events import validate_event_chain
from zecsolve.domain.packets import component, decoded_transaction_hash, parse_packet, seal_packet
from zecsolve.domain.snapshots import digest
from zecsolve.schemas.packet import CasePacketV1, PacketComponentV1


@pytest.mark.parametrize("name", ["complete-v1", "complete-v2", "scoped"])
def test_public_synthetic_fixtures_validate_and_preserve_original_hash_bases(root, name):
    packet = parse_packet((root / f"fixtures/packets/{name}.json").read_bytes())
    item = packet.payload.evidence[0]
    receipt = (root / "fixtures/mainnet/receipt.json").read_bytes()
    raw = (root / "fixtures/mainnet/transaction.hex").read_bytes()
    assert item.receipt.text().encode() == receipt
    assert item.receipt.sha256 == hashlib.sha256(receipt).hexdigest()
    assert item.raw_transaction_hex.text().encode() == raw
    assert item.raw_transaction_hex.sha256 == hashlib.sha256(raw).hexdigest()
    assert (
        item.decoded_transaction_sha256
        == hashlib.sha256(bytes.fromhex(raw.decode().strip())).hexdigest()
    )
    assert item.decoded_transaction_sha256 != item.raw_transaction_hex.sha256
    assert seal_packet(packet.payload) == packet
    assert packet.payload.report.verifications[0].result.verifier.version == "0.1.0"
    if name != "scoped":
        report = packet.payload.report
        validate_event_chain(report.events, report.case.case_id, report.case.version)
        assert (
            digest(report.invoice.model_dump(mode="json", exclude={"created_at", "snapshot_hash"}))
            == report.invoice.snapshot_hash
        )
        for snapshot in report.evaluations + report.decision_evaluations:
            assert (
                digest(snapshot.model_dump(mode="json", exclude={"snapshot_hash"}))
                == snapshot.snapshot_hash
            )
        assert report.decision_evaluations[0].result.rules_version == "0.2.0"
        assert report.evaluations[0].result.rules_version == "0.1.0"
        assert report.decisions[0].evaluation.observation.source_kind == "SIMULATED"
        assert report.evidence[0].schema_version == ("2" if name == "complete-v2" else "1")
        assert item.submission_payload.sha256 == report.evidence[0].payload_sha256
        assert report.events[1].schema_version == report.evidence[0].schema_version
    else:
        assert packet.payload.replay_scope == "LIMITED"
        assert item.submission_payload.availability == "OMITTED"
        assert packet.payload.balance_context is None
        assert packet.payload.omissions


def test_scoped_packet_cannot_claim_full_history_or_include_private_submission(root):
    raw = json.loads((root / "fixtures/packets/scoped.json").read_text())
    raw["payload"]["replay_scope"] = "FULL_HISTORY"
    with pytest.raises(ValidationError):
        CasePacketV1.model_validate(raw)
    raw["payload"]["replay_scope"] = "LIMITED"
    raw["payload"]["evidence"][0]["submission_payload"] = component("{}").model_dump()
    with pytest.raises(ValidationError):
        CasePacketV1.model_validate(raw)


@pytest.mark.parametrize("value", [None, "", ' \n{"note":"é"}\n', "Aa\n00"])
def test_exact_component_null_empty_unicode_and_original_hex(value):
    item = component(value)
    assert item.text() == value
    assert (item.availability == "NOT_SUBMITTED") == (value is None)
    if value is not None:
        assert item.sha256 == hashlib.sha256(value.encode("utf-8")).hexdigest()
    assert component(value, omitted=True).data is None


@pytest.mark.parametrize("data", ["!!!!", "eA", "eB==", "/w=="])
def test_components_reject_noncanonical_base64_and_non_utf8(data):
    with pytest.raises(ValueError):
        PacketComponentV1(availability="PRESENT", data=data, sha256="ab" * 32)


def test_integrity_hashes_raw_payload_before_defaults_and_rejects_ambiguous_json(root):
    path = root / "fixtures/packets/complete-v1.json"
    raw = json.loads(path.read_text())
    raw["payload"]["report"]["decisions"][0]["reason"] += "!"
    with pytest.raises(ValueError, match="integrity"):
        parse_packet(json.dumps(raw).encode())
    duplicated = path.read_bytes().replace(
        b'"schema_version": "case-packet-v1",',
        b'"schema_version": "case-packet-v1", "schema_version": "case-packet-v1",',
        1,
    )
    with pytest.raises(ValueError, match="Duplicate"):
        parse_packet(duplicated)
    assert decoded_transaction_hash("invalid-hex") is None
    assert decoded_transaction_hash(None) is None
    assert decoded_transaction_hash("") == hashlib.sha256(b"").hexdigest()
