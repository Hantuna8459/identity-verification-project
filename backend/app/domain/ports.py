from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class StoredEvidence:
    storage_key: str
    size_bytes: int
    sha256: str


class EvidenceStorage(Protocol):
    def put(self, session_id: uuid.UUID, evidence_type: str, payload: bytes) -> StoredEvidence: ...

    def get(self, storage_key: str) -> bytes: ...

    def delete(self, storage_key: str) -> None: ...


@dataclass(frozen=True)
class EvidencePayload:
    evidence_type: str
    content_type: str
    payload: bytes


class EkycAnalyzer(Protocol):
    def analyze(
        self,
        session_id: uuid.UUID,
        document_type: str,
        voice_challenge: str,
        evidence: list[EvidencePayload],
    ) -> dict[str, Any]: ...


class WebhookNotifier(Protocol):
    def session_changed(self, session_id: uuid.UUID, stage: str, decision: str) -> None: ...
