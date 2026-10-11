import base64
import os
import re
import uuid
from dataclasses import dataclass, field

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr

from zecsolve.domain.snapshots import canonical_bytes
from zecsolve.schemas.evidence import MAX_EVIDENCE_PAYLOAD_BYTES


class EvidenceEncryptionError(Exception):
    pass


@dataclass(frozen=True)
class EncryptedEvidence:
    key_id: str
    nonce: bytes
    ciphertext: bytes = field(repr=False)


class EvidenceCipher:
    def __init__(self, key_id: str, encoded_key: SecretStr):
        self.key_id = key_id
        self._aes = None
        try:
            key = base64.b64decode(encoded_key.get_secret_value(), validate=True)
            if re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", key_id) and len(key) == 32:
                self._aes = AESGCM(key)
        except ValueError:
            pass

    @property
    def available(self) -> bool:
        return self._aes is not None

    def associated_data(
        self, merchant_id: uuid.UUID, case_id: uuid.UUID, evidence_id: uuid.UUID
    ) -> bytes:
        return canonical_bytes(
            {
                "payload_version": "1",
                "key_id": self.key_id,
                "merchant_id": str(merchant_id),
                "case_id": str(case_id),
                "evidence_id": str(evidence_id),
            }
        )

    def encrypt(self, plaintext: bytes, **context) -> EncryptedEvidence:
        if not self.available:
            raise EvidenceEncryptionError("EVIDENCE_ENCRYPTION_UNAVAILABLE")
        if len(plaintext) > MAX_EVIDENCE_PAYLOAD_BYTES:
            raise EvidenceEncryptionError("EVIDENCE_TOO_LARGE")
        nonce = os.urandom(12)
        return EncryptedEvidence(
            self.key_id, nonce, self._aes.encrypt(nonce, plaintext, self.associated_data(**context))
        )

    def decrypt(self, sealed: EncryptedEvidence, **context) -> bytes:
        if not self.available or sealed.key_id != self.key_id:
            raise EvidenceEncryptionError("EVIDENCE_KEY_UNAVAILABLE")
        if (
            len(sealed.nonce) != 12
            or not 16 <= len(sealed.ciphertext) <= MAX_EVIDENCE_PAYLOAD_BYTES + 16
        ):
            raise EvidenceEncryptionError("EVIDENCE_INTEGRITY_ERROR")
        try:
            return self._aes.decrypt(
                sealed.nonce, sealed.ciphertext, self.associated_data(**context)
            )
        except (InvalidTag, ValueError):
            raise EvidenceEncryptionError("EVIDENCE_INTEGRITY_ERROR") from None
