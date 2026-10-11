import base64
import os
import uuid
from dataclasses import replace

import pytest
from pydantic import SecretStr


def test_evidence_cipher_roundtrip_random_nonces_and_context_binding():
    from zecsolve.adapters.evidence_crypto import EvidenceCipher, EvidenceEncryptionError

    cipher = EvidenceCipher("test-key", SecretStr(base64.b64encode(os.urandom(32)).decode()))
    context = dict(merchant_id=uuid.uuid4(), case_id=uuid.uuid4(), evidence_id=uuid.uuid4())
    raw = b' {"receipt":"private selected output"}\n\0'
    first = cipher.encrypt(raw, **context)
    second = cipher.encrypt(raw, **context)
    assert len(first.nonce) == 12 and first.nonce != second.nonce
    assert raw not in first.ciphertext
    assert cipher.decrypt(first, **context) == raw
    for name in context:
        with pytest.raises(EvidenceEncryptionError, match="INTEGRITY"):
            cipher.decrypt(first, **{**context, name: uuid.uuid4()})
    with pytest.raises(EvidenceEncryptionError, match="INTEGRITY"):
        cipher.decrypt(
            replace(first, ciphertext=first.ciphertext[:-1] + bytes([first.ciphertext[-1] ^ 1])),
            **context,
        )
    with pytest.raises(EvidenceEncryptionError, match="KEY_UNAVAILABLE"):
        cipher.decrypt(replace(first, key_id="different"), **context)


@pytest.mark.parametrize("value", ["", "bad-key", base64.b64encode(bytes(16)).decode(), "é"])
def test_unconfigured_or_invalid_encryption_key_fails_closed(value):
    from zecsolve.adapters.evidence_crypto import EvidenceCipher, EvidenceEncryptionError

    cipher = EvidenceCipher("test-key", SecretStr(value))
    assert not cipher.available
    with pytest.raises(EvidenceEncryptionError, match="ENCRYPTION_UNAVAILABLE"):
        cipher.encrypt(
            b"private", merchant_id=uuid.uuid4(), case_id=uuid.uuid4(), evidence_id=uuid.uuid4()
        )


def test_key_is_redacted_and_payload_is_bounded():
    from zecsolve.adapters.evidence_crypto import EvidenceCipher, EvidenceEncryptionError
    from zecsolve.config import Settings

    encoded = base64.b64encode(os.urandom(32)).decode()
    settings = Settings(_env_file=None, evidence_key_id="test", evidence_key=encoded)
    assert encoded not in repr(settings)
    cipher = EvidenceCipher(settings.evidence_key_id, settings.evidence_key)
    assert encoded not in repr(cipher)
    with pytest.raises(EvidenceEncryptionError, match="TOO_LARGE"):
        cipher.encrypt(
            bytes(4_200_001),
            merchant_id=uuid.uuid4(),
            case_id=uuid.uuid4(),
            evidence_id=uuid.uuid4(),
        )
