"""Packet serialization only: no database, permissions, execution or network access."""

import base64
import hashlib
import json

from zecsolve.domain.snapshots import digest
from zecsolve.schemas.packet import (
    MAX_PACKET_BYTES,
    CasePacketV1,
    PacketComponentV1,
    PacketImplementationsV1,
    PacketIntegrityV1,
    PacketVerifierV1,
)

ASSERTIONS = [
    "INVOICE_AND_CLAIMS_ARE_BUSINESS_ASSERTIONS",
    "OBSERVATIONS_ARE_HISTORICAL_EXTERNAL_ASSERTIONS",
    "ALLOCATION_AND_SOURCE_AUTHORITY_ARE_EXTERNAL_ASSERTIONS",
    "HASHES_DO_NOT_AUTHENTICATE_AUTHOR",
]


def component(value, *, omitted=False):
    raw = value.encode("utf-8") if value is not None and not omitted else None
    return PacketComponentV1(
        availability="OMITTED" if omitted else ("NOT_SUBMITTED" if raw is None else "PRESENT"),
        data=base64.b64encode(raw).decode("ascii") if raw is not None else None,
        sha256=hashlib.sha256(raw).hexdigest() if raw is not None else None,
    )


def decoded_transaction_hash(raw):
    if raw is None:
        return None
    try:
        return hashlib.sha256(bytes.fromhex(raw.strip())).hexdigest()
    except ValueError:
        return None


def implementations(report):
    verifiers = {}
    rules = set()
    for item in report.verifications or []:
        identity = PacketVerifierV1(
            name=item.result.verifier.name,
            version=item.result.verifier.version,
            result_schema_version=item.result.schema_version,
            glasspane_revision=item.result.verifier.glasspane_revision,
        )
        verifiers[identity.model_dump_json()] = identity
    for item in report.evaluations or []:
        rules.add(item.result.rules_version)
    for item in getattr(report, "decision_evaluations", []):
        rules.add(item.result.rules_version)
    if report.balances:
        rules.add(report.balances.rules_version)
    return PacketImplementationsV1(verifiers=list(verifiers.values()), rules=sorted(rules))


def seal_packet(payload):
    return CasePacketV1(
        payload=payload,
        integrity=PacketIntegrityV1(payload_sha256=digest(payload.model_dump(mode="json"))),
    )


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def parse_packet(data: bytes):
    if len(data) > MAX_PACKET_BYTES:
        raise ValueError("Packet exceeds size limit")
    # Hash the supplied JSON before model defaults/normalization can alter it.
    raw = json.loads(data.decode("utf-8"), object_pairs_hook=unique_object)
    if not isinstance(raw, dict) or raw.get("schema_version") != "case-packet-v1":
        raise ValueError("Unsupported packet schema")
    if digest(raw["payload"]) != raw["integrity"]["payload_sha256"]:
        raise ValueError("Packet integrity mismatch")
    return CasePacketV1.model_validate(raw)
