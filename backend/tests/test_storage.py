from __future__ import annotations

import uuid

import pytest

from app.adapters.storage import EncryptedLocalEvidenceStorage


def test_local_evidence_is_encrypted_and_round_trips(tmp_path) -> None:
    storage = EncryptedLocalEvidenceStorage(tmp_path, "test-key")
    payload = b"synthetic-sensitive-evidence"
    stored = storage.put(uuid.uuid4(), "DOCUMENT_FRONT", payload)
    raw_file = (tmp_path / stored.storage_key).read_bytes()
    assert payload not in raw_file
    assert storage.get(stored.storage_key) == payload
    storage.delete(stored.storage_key)
    assert not (tmp_path / stored.storage_key).exists()


def test_storage_rejects_path_traversal(tmp_path) -> None:
    storage = EncryptedLocalEvidenceStorage(tmp_path, "test-key")
    with pytest.raises(ValueError, match="Invalid evidence storage key"):
        storage.get("../../outside")
