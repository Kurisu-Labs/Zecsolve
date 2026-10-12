import importlib.util
import os

import pytest
from cryptography.exceptions import InvalidTag


@pytest.fixture
def backup(root):
    spec = importlib.util.spec_from_file_location(
        "recovery_backup", root / "scripts/recovery_backup.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backup_roundtrip_has_fresh_nonces_and_rejects_wrong_key(backup):
    key, data = os.urandom(32), b"PGDMP\0synthetic private claim"
    first, second = backup.seal(key, data), backup.seal(key, data)
    assert first != second and data not in first
    assert backup.unseal(key, first) == data
    with pytest.raises(InvalidTag):
        backup.unseal(os.urandom(32), first)


@pytest.mark.parametrize("part", ["header", "nonce", "ciphertext", "truncate"])
def test_backup_rejects_tampered_or_truncated_archive(backup, part):
    key = os.urandom(32)
    value = bytearray(backup.seal(key, b"PGDMP\0synthetic"))
    if part == "truncate":
        value = value[:-1]
    else:
        index = {"header": 0, "nonce": len(backup.MAGIC), "ciphertext": -1}[part]
        value[index] ^= 1
    with pytest.raises((ValueError, InvalidTag)):
        backup.unseal(key, bytes(value))


def test_backup_rejects_non_archive_and_unbounded_payload(backup, monkeypatch):
    key = os.urandom(32)
    with pytest.raises(ValueError):
        backup.seal(key, b"not a PostgreSQL archive")
    monkeypatch.setattr(backup, "LIMIT", 10)
    with pytest.raises(ValueError):
        backup.seal(key, b"PGDMP" + bytes(10))
