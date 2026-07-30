from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any


class OfflineModelAnalyzer:
    """Fail-safe adapter boundary for pinned pretrained model artifacts.

    Artifact readiness is deliberately separate from pipeline readiness. Until the
    benchmarked orchestration is implemented, submissions always enter manual review.
    """

    def __init__(self, model_dir: Path, require_models: bool = False) -> None:
        self._model_dir = model_dir
        self._require_models = require_models

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def readiness(self) -> dict[str, Any]:
        manifest = self._model_dir / "manifest.json"
        if not manifest.is_file():
            return {
                "ready": not self._require_models,
                "artifact_ready": False,
                "pipeline_ready": False,
                "manifest": False,
                "models": [],
                "invalid": ["manifest.json"],
            }
        data = json.loads(manifest.read_text(encoding="utf-8"))
        invalid: list[str] = []
        model_ids: list[str] = []
        for entry in data.get("models", []):
            model_id = str(entry.get("id", "unknown"))
            model_ids.append(model_id)
            if not entry.get("required"):
                continue
            path = self._model_dir / str(entry["path"])
            if not path.is_file():
                invalid.append(f"{model_id}:missing")
            elif path.stat().st_size != int(entry["size_bytes"]):
                invalid.append(f"{model_id}:size")
            elif self._sha256(path) != entry["sha256"]:
                invalid.append(f"{model_id}:sha256")
        artifact_ready = not invalid
        return {
            "ready": artifact_ready,
            "artifact_ready": artifact_ready,
            "pipeline_ready": False,
            "manifest": True,
            "models": model_ids,
            "invalid": invalid,
        }

    def analyze(self, session_id: uuid.UUID, evidence_types: set[str]) -> dict[str, Any]:
        state = self.readiness()
        if self._require_models and not state["artifact_ready"]:
            raise RuntimeError(f"Required offline model artifacts invalid: {state['invalid']}")
        return {
            "schema_version": "1.0",
            "session_id": str(session_id),
            "pipeline": "offline-pretrained-adapter",
            "model_readiness": state,
            "evidence_types": sorted(evidence_types),
            "decision_candidate": "MANUAL_REVIEW",
            "reason_codes": ["MODEL_PIPELINE_REQUIRES_BENCHMARKED_IMPLEMENTATION"],
        }
