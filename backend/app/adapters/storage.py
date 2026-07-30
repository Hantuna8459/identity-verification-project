from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.domain.ports import StoredEvidence


class EncryptedLocalEvidenceStorage:
    def __init__(self, root: Path, secret: str) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._cipher = AESGCM(hashlib.sha256(secret.encode("utf-8")).digest())

    def put(self, session_id: uuid.UUID, evidence_type: str, payload: bytes) -> StoredEvidence:
        storage_key = f"{session_id}/{evidence_type.lower()}-{uuid.uuid4().hex}.enc"
        destination = self._resolve(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        nonce = os.urandom(12)
        encrypted = nonce + self._cipher.encrypt(nonce, payload, storage_key.encode("utf-8"))
        temporary = destination.with_suffix(".tmp")
        temporary.write_bytes(encrypted)
        temporary.replace(destination)
        return StoredEvidence(
            storage_key=storage_key,
            size_bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
        )

    def get(self, storage_key: str) -> bytes:
        encrypted = self._resolve(storage_key).read_bytes()
        nonce, ciphertext = encrypted[:12], encrypted[12:]
        return self._cipher.decrypt(nonce, ciphertext, storage_key.encode("utf-8"))

    def delete(self, storage_key: str) -> None:
        destination = self._resolve(storage_key)
        destination.unlink(missing_ok=True)
        parent = destination.parent
        if parent != self._root:
            try:
                parent.rmdir()
            except OSError:
                pass

    def _resolve(self, storage_key: str) -> Path:
        destination = (self._root / storage_key).resolve()
        if self._root not in destination.parents:
            raise ValueError("Invalid evidence storage key")
        return destination
