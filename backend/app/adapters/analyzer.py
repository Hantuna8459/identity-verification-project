from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from ai_modules.ekyc.pipeline import TechnicalDemoPipeline
from app.domain.ports import EvidencePayload


class OfflineModelAnalyzer:
    """Adapter for pinned, profile-approved offline technical-demo models."""

    def __init__(
        self,
        model_dir: Path,
        require_models: bool = False,
        *,
        profile: str = "technical_demo",
        device: str = "cpu",
        lipsync_url: str | None = None,
        max_video_frames: int = 12,
    ) -> None:
        self._model_dir = model_dir
        self._require_models = require_models
        self._profile = profile
        self._pipeline = TechnicalDemoPipeline(
            model_dir,
            device=device,
            lipsync_url=lipsync_url,
            max_video_frames=max_video_frames,
        )

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _artifacts(entry: dict[str, Any]) -> list[dict[str, Any]]:
        artifacts = entry.get("artifacts")
        return artifacts if isinstance(artifacts, list) else [entry]

    def readiness(self) -> dict[str, Any]:
        manifest = self._model_dir / "manifest.json"
        if not manifest.is_file():
            return {
                "ready": not self._require_models,
                "artifact_ready": False,
                "pipeline_ready": False,
                "production_ready": False,
                "profile": self._profile,
                "manifest": False,
                "models": [],
                "invalid": ["manifest.json:missing"],
            }
        data = json.loads(manifest.read_text(encoding="utf-8"))
        invalid: list[str] = []
        model_ids: list[str] = []
        statuses: dict[str, str] = {}
        for entry in data.get("models", []):
            model_id = str(entry.get("id", "unknown"))
            status = str(entry.get("approval_status", "quarantined"))
            scopes = entry.get("usage_scope", [])
            if status not in {"evaluation_only", "production_approved"}:
                continue
            if self._profile not in scopes and "all" not in scopes:
                continue
            model_ids.append(model_id)
            statuses[model_id] = status
            if not entry.get("required"):
                continue
            for artifact in self._artifacts(entry):
                path = self._model_dir / str(artifact["path"])
                label = f"{model_id}:{artifact['path']}"
                if not path.is_file():
                    invalid.append(f"{label}:missing")
                elif path.stat().st_size != int(artifact["size_bytes"]):
                    invalid.append(f"{label}:size")
                elif self._sha256(path) != artifact["sha256"]:
                    invalid.append(f"{label}:sha256")
        artifact_ready = not invalid
        production_ready = (
            bool(model_ids)
            and artifact_ready
            and all(value == "production_approved" for value in statuses.values())
        )
        return {
            "ready": artifact_ready if self._require_models else True,
            "artifact_ready": artifact_ready,
            "pipeline_ready": artifact_ready,
            "production_ready": production_ready,
            "profile": self._profile,
            "manifest": True,
            "models": model_ids,
            "approval_statuses": statuses,
            "invalid": invalid,
        }

    @classmethod
    def _collect_statuses(cls, value: Any) -> list[str]:
        if isinstance(value, dict):
            statuses = [str(value["status"])] if "status" in value else []
            for child in value.values():
                statuses.extend(cls._collect_statuses(child))
            return statuses
        if isinstance(value, list):
            return [status for child in value for status in cls._collect_statuses(child)]
        return []

    def analyze(
        self,
        session_id: uuid.UUID,
        document_type: str,
        voice_challenge: str,
        evidence: list[EvidencePayload],
    ) -> dict[str, Any]:
        readiness = self.readiness()
        if readiness["artifact_ready"]:
            capabilities = self._pipeline.analyze(document_type, voice_challenge, evidence)
        else:
            capabilities = {
                name: {
                    "status": "UNAVAILABLE",
                    "reason": "REQUIRED_MODEL_ARTIFACT_INVALID",
                }
                for name in (
                    "ocr",
                    "face_match",
                    "liveness",
                    "active_liveness",
                    "visual_deepfake",
                    "voice_challenge",
                    "lip_sync",
                )
            }
        statuses = self._collect_statuses(capabilities)
        reason_codes = ["TECHNICAL_DEMO_MANUAL_REVIEW"]
        if not readiness["artifact_ready"] or "UNAVAILABLE" in statuses:
            reason_codes.append("MODEL_UNAVAILABLE")
        if "INCONCLUSIVE" in statuses:
            reason_codes.append("AI_RESULT_INCONCLUSIVE")
        active_liveness = capabilities.get("active_liveness", {})
        if (
            isinstance(active_liveness, dict)
            and active_liveness.get("reason") == "CHALLENGE_SEQUENCE_INCOMPLETE"
        ):
            reason_codes.append("ACTIVE_LIVENESS_SEQUENCE_INCOMPLETE")
        return {
            "schema_version": "1.1",
            "session_id": str(session_id),
            "pipeline": "offline-technical-demo",
            "profile": self._profile,
            "model_readiness": readiness,
            "evidence_types": sorted(item.evidence_type for item in evidence),
            "capabilities": capabilities,
            "decision_candidate": "MANUAL_REVIEW",
            "reason_codes": reason_codes,
        }
