"""Bounded encrypted archive envelope for disposable recovery fixtures, not a backup service."""

import base64
import json
import os
import sys

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"zecsolve-rehearsal-backup-v1\0"
LIMIT = 64 * 1024 * 1024


def seal(key, data):
    if len(key) != 32 or not data.startswith(b"PGDMP") or len(data) > LIMIT:
        raise ValueError("Invalid rehearsal archive")
    nonce = os.urandom(12)
    return MAGIC + nonce + AESGCM(key).encrypt(nonce, data, MAGIC)


def unseal(key, archive):
    if len(key) != 32 or not archive.startswith(MAGIC):
        raise ValueError("Invalid rehearsal archive")
    body = archive[len(MAGIC) :]
    if not 28 <= len(body) <= LIMIT + 28:
        raise ValueError("Invalid rehearsal archive")
    data = AESGCM(key).decrypt(body[:12], body[12:], MAGIC)
    if not data.startswith(b"PGDMP"):
        raise ValueError("Invalid rehearsal archive")
    return data


if __name__ == "__main__":
    # Input/output pipes are private to the harness; key material never enters argv or logs.
    try:
        request = json.loads(sys.stdin.buffer.read((LIMIT + 1024) * 2))
        key = base64.b64decode(request["key"], validate=True)
        data = base64.b64decode(request["data"], validate=True)
        action = {"seal": seal, "unseal": unseal}[request["action"]]
        result = {"ok": True, "data": base64.b64encode(action(key, data)).decode()}
    except (ValueError, KeyError, InvalidTag):
        result = {"ok": False}
    print(json.dumps(result))
