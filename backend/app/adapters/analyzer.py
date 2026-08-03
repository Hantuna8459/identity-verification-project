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
        max_video_frames: int = 36,
        max_face_match_frames: int = 12,
        replay_suspicious_threshold: float = 0.62,
        camera_injection_suspicious_threshold: float = 0.60,
    ) -> None:
        self._model_dir = model_dir
        self._require_models = require_models
        self._profile = profile
        self._pipeline = TechnicalDemoPipeline(
            model_dir,
            device=device,
            lipsync_url=lipsync_url,
            max_video_frames=max_video_frames,
            max_face_match_frames=max_face_match_frames,
            replay_suspicious_threshold=replay_suspicious_threshold,
            camera_injection_suspicious_threshold=camera_injection_suspicious_threshold,
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
            status = value.get("execution_status", value.get("status"))
            statuses = [str(status)] if status is not None else []
            for child in value.values():
                statuses.extend(cls._collect_statuses(child))
            return statuses
        if isinstance(value, list):
            return [status for child in value for status in cls._collect_statuses(child)]
        return []

    @staticmethod
    def _execution_status(value: dict[str, Any]) -> str:
        return {
            "OK": "COMPLETED",
            "INCONCLUSIVE": "INCONCLUSIVE",
            "UNAVAILABLE": "UNAVAILABLE",
        }.get(str(value.get("status", "UNAVAILABLE")), "ERROR")

    @classmethod
    def _normalize_nested_statuses(cls, value: Any) -> Any:
        if isinstance(value, dict):
            normalized = {
                key: cls._normalize_nested_statuses(child)
                for key, child in value.items()
                if key != "status"
            }
            if "status" in value:
                normalized["execution_status"] = cls._execution_status(value)
            return normalized
        if isinstance(value, list):
            return [cls._normalize_nested_statuses(child) for child in value]
        return value

    @classmethod
    def _base_output(
        cls,
        value: dict[str, Any],
        *,
        review_signal: str,
        metrics: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
        reason_codes: list[str] | None = None,
        threshold: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        output: dict[str, Any] = {
            "execution_status": cls._execution_status(value),
            "review_signal": review_signal,
            "reason_codes": reason_codes or [],
        }
        if value.get("engine") is not None:
            output["engine"] = value["engine"]
        if metrics:
            output["metrics"] = metrics
        if threshold is not None:
            output["threshold"] = threshold
        if details:
            output["details"] = details
        if value.get("error_type") is not None:
            output["error_type"] = value["error_type"]
        if value.get("reason") is not None and not output["reason_codes"]:
            output["reason_codes"] = [str(value["reason"])]
        return output

    @classmethod
    def _normalize_capability(cls, name: str, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {
                "execution_status": "ERROR",
                "review_signal": "INVALID_MODEL_OUTPUT",
                "reason_codes": ["INVALID_MODEL_OUTPUT"],
            }

        execution_status = cls._execution_status(value)
        if execution_status != "COMPLETED" and name != "active_liveness":
            return cls._base_output(value, review_signal=execution_status)

        if name == "face_match":
            return cls._base_output(
                value,
                review_signal="SCORE_AVAILABLE",
                metrics={
                    "cosine_similarity": value.get("cosine_similarity"),
                    "score_direction": "HIGHER_IS_MORE_SIMILAR",
                },
                threshold={"value": None, "approval_status": "NOT_APPROVED"},
                details={
                    "sampled_frames": value.get("sampled_frames"),
                    "frames_with_face": value.get("frames_with_face"),
                    "matched_frames": value.get("matched_frames"),
                    "aggregation": value.get("aggregation"),
                },
                reason_codes=["FACE_MATCH_THRESHOLD_NOT_APPROVED"],
            )
        if name == "liveness":
            return cls._base_output(
                value,
                review_signal="SCORE_AVAILABLE",
                metrics={
                    "live_probability": value.get("live_probability"),
                    "score_direction": "HIGHER_IS_MORE_LIVE_LIKE",
                },
                threshold={"value": None, "approval_status": "NOT_APPROVED"},
                reason_codes=["LIVENESS_THRESHOLD_NOT_APPROVED"],
            )
        if name == "visual_deepfake":
            return cls._base_output(
                value,
                review_signal="SCORE_AVAILABLE",
                metrics={
                    "manipulation_probability": value.get("manipulation_probability"),
                    "score_direction": "HIGHER_IS_MORE_SUSPICIOUS",
                },
                threshold={"value": None, "approval_status": "NOT_APPROVED"},
                reason_codes=["DEEPFAKE_THRESHOLD_NOT_APPROVED"],
            )
        if name == "active_liveness":
            complete = value.get("sequence_complete") is True
            return cls._base_output(
                value,
                review_signal="CHALLENGE_COMPLETE" if complete else "CHALLENGE_INCOMPLETE",
                details={
                    "sequence_complete": complete,
                    "completed_step_count": value.get("completed_step_count"),
                    "required_step_count": value.get("required_step_count"),
                    "sampled_pose_count": value.get("sampled_pose_count"),
                },
                reason_codes=[] if complete else ["CHALLENGE_SEQUENCE_INCOMPLETE"],
            )
        if name == "voice_challenge":
            expected = int(value.get("challenge_length", 0) or 0)
            recognized = int(value.get("recognized_digit_count", 0) or 0)
            similarity = float(value.get("similarity", 0.0) or 0.0)
            matched = expected > 0 and recognized == expected and similarity == 1.0
            return cls._base_output(
                value,
                review_signal="CHALLENGE_MATCH" if matched else "CHALLENGE_MISMATCH",
                metrics={"similarity": similarity, "score_direction": "HIGHER_IS_BETTER"},
                details={
                    "challenge_length": expected,
                    "recognized_digit_count": recognized,
                },
                reason_codes=[] if matched else ["VOICE_CHALLENGE_MISMATCH"],
            )
        if name == "lip_sync":
            verdict = str(value.get("verdict", "")).lower()
            signal = (
                "SUSPICIOUS"
                if verdict == "fake"
                else "NO_SUSPICIOUS_SIGNAL"
                if verdict == "real"
                else "INCONCLUSIVE"
            )
            return cls._base_output(
                value,
                review_signal=signal,
                metrics={
                    "confidence": value.get("confidence"),
                    "manipulation_probability": value.get("manipulation_probability"),
                    "score_direction": "HIGHER_IS_MORE_SUSPICIOUS",
                },
                details={"model_verdict": value.get("verdict")},
                reason_codes=["LIP_SYNC_SUSPICIOUS"] if signal == "SUSPICIOUS" else [],
            )
        if name in {"replay_attack", "camera_injection"}:
            suspicious = value.get("suspicious") is True
            metric_keys = (
                "score",
                "moire_score",
                "flicker_score",
                "duplication_score",
                "face_motion_score",
                "metadata_score",
                "challenge_timing_score",
            )
            return cls._base_output(
                value,
                review_signal="SUSPICIOUS" if suspicious else "NO_SUSPICIOUS_SIGNAL",
                metrics={
                    **{key: value[key] for key in metric_keys if key in value},
                    "score_direction": "HIGHER_IS_MORE_SUSPICIOUS",
                },
                threshold={
                    "value": value.get("threshold"),
                    "approval_status": "EVALUATION_ONLY",
                },
                details={
                    key: value[key]
                    for key in (
                        "confirmed",
                        "duplicate_pairs",
                        "sampled_frame_count",
                        "warnings",
                    )
                    if key in value
                },
                reason_codes=[str(code) for code in value.get("reason_codes", [])],
            )
        return cls._base_output(value, review_signal="OBSERVED")

    @classmethod
    def normalize_capabilities(cls, capabilities: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for name, value in capabilities.items():
            if name != "ocr":
                normalized[name] = cls._normalize_capability(name, value)
                continue
            if not isinstance(value, dict) or "status" in value:
                normalized[name] = cls._normalize_capability(name, value)
                continue
            documents = {
                document: cls._base_output(
                    result,
                    review_signal=(
                        "TEXT_DETECTED"
                        if cls._execution_status(result) == "COMPLETED"
                        else cls._execution_status(result)
                    ),
                    metrics={
                        key: result[key]
                        for key in ("line_count", "mean_confidence")
                        if key in result
                    },
                    details=cls._normalize_nested_statuses(
                        {key: result[key] for key in ("layout", "mrz") if key in result}
                    ),
                )
                for document, result in value.items()
                if isinstance(result, dict)
            }
            document_statuses = [item["execution_status"] for item in documents.values()]
            aggregate_status = (
                "UNAVAILABLE"
                if "UNAVAILABLE" in document_statuses
                else "INCONCLUSIVE"
                if "INCONCLUSIVE" in document_statuses
                else "COMPLETED"
            )
            normalized[name] = {
                "execution_status": aggregate_status,
                "review_signal": (
                    "TEXT_DETECTED" if aggregate_status == "COMPLETED" else aggregate_status
                ),
                "reason_codes": [],
                "documents": documents,
            }
        return normalized

    def analyze_document(
        self,
        document_type: str,
        evidence: list[EvidencePayload],
    ) -> dict[str, Any]:
        readiness = self.readiness()
        expected_types = (
            ["PASSPORT_PAGE"]
            if document_type == "PASSPORT_TD3"
            else ["DOCUMENT_FRONT", "DOCUMENT_BACK"]
        )
        if readiness["artifact_ready"]:
            results = self._pipeline.analyze_ocr(document_type, evidence)
        else:
            results = {
                evidence_type.lower(): {
                    "status": "UNAVAILABLE",
                    "reason": "REQUIRED_MODEL_ARTIFACT_INVALID",
                }
                for evidence_type in expected_types
            }

        documents: dict[str, Any] = {}
        for evidence_type, result in results.items():
            document: dict[str, Any] = {
                "execution_status": self._execution_status(result),
                "lines": [str(line) for line in result.get("lines", [])],
            }
            if result.get("engine") is not None:
                document["engine"] = result["engine"]
            if isinstance(result.get("mrz"), dict):
                document["mrz_validation"] = self._normalize_nested_statuses(result["mrz"])
            if result.get("reason") is not None:
                document["reason_codes"] = [str(result["reason"])]
            if result.get("error_type") is not None:
                document["error_type"] = str(result["error_type"])
            documents[evidence_type] = document

        return {
            "schema_version": "demo-ocr-rerun/1.0",
            "transient": True,
            "documents": documents,
        }

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
                    "replay_attack",
                    "camera_injection",
                    "visual_deepfake",
                    "voice_challenge",
                    "lip_sync",
                )
            }
        capabilities = self.normalize_capabilities(capabilities)
        statuses = self._collect_statuses(capabilities)
        reason_codes = ["TECHNICAL_DEMO_MANUAL_REVIEW"]
        if not readiness["artifact_ready"] or "UNAVAILABLE" in statuses:
            reason_codes.append("MODEL_UNAVAILABLE")
        if "INCONCLUSIVE" in statuses:
            reason_codes.append("AI_RESULT_INCONCLUSIVE")
        for capability, reason in (
            ("replay_attack", "REPLAY_ATTACK_SUSPECTED"),
            ("camera_injection", "CAMERA_INJECTION_SUSPECTED"),
            ("lip_sync", "LIP_SYNC_SUSPICIOUS"),
        ):
            signal = capabilities.get(capability, {})
            if isinstance(signal, dict) and signal.get("review_signal") == "SUSPICIOUS":
                reason_codes.append(reason)
        voice_challenge = capabilities.get("voice_challenge", {})
        if (
            isinstance(voice_challenge, dict)
            and voice_challenge.get("review_signal") == "CHALLENGE_MISMATCH"
        ):
            reason_codes.append("VOICE_CHALLENGE_MISMATCH")
        active_liveness = capabilities.get("active_liveness", {})
        if (
            isinstance(active_liveness, dict)
            and active_liveness.get("review_signal") == "CHALLENGE_INCOMPLETE"
        ):
            reason_codes.append("ACTIVE_LIVENESS_SEQUENCE_INCOMPLETE")
        return {
            "schema_version": "model-analysis/1.2",
            "session_id": str(session_id),
            "pipeline": "offline-technical-demo",
            "profile": self._profile,
            "model_readiness": readiness,
            "evidence_types": sorted(item.evidence_type for item in evidence),
            "capabilities": capabilities,
            "decision_candidate": "MANUAL_REVIEW",
            "reason_codes": reason_codes,
        }
