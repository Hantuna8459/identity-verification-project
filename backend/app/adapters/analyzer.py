from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.adapters.capability_registry import CapabilityRegistry
from app.adapters.ekyc_orchestrator import EkycOrchestrator
from app.domain.ports import EvidencePayload


class OfflineModelAnalyzer:
    """Adapter for pinned, profile-approved offline technical-demo models.

    Concrete provider/model selection lives entirely in `CapabilityRegistry`
    (composition root, per ADR-M0-001) - this class only owns the
    `ekyc-analysis/1.0` envelope/normalization contract on top of whatever
    `EkycOrchestrator` returns.
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
        require_models: bool = False,
        *,
        profile: str = "technical_demo",
        max_video_frames: int = 36,
        max_face_match_frames: int = 12,
        replay_suspicious_threshold: float = 0.62,
        camera_injection_suspicious_threshold: float = 0.60,
        face_match_threshold: float = 0.45,
        face_match_consider_threshold: float = 0.30,
        passive_liveness_threshold: float = 0.65,
        passive_liveness_consider_threshold: float = 0.45,
        visual_deepfake_threshold: float = 0.68,
        face_quality_min_video_face_frames: int = 8,
        face_quality_blur_threshold: float = 60.0,
        face_quality_min_coverage: float = 0.08,
        face_quality_max_coverage: float = 0.65,
        face_quality_yaw_threshold: float = 0.08,
        face_quality_roll_threshold: float = 0.35,
    ) -> None:
        self._registry = registry
        self._require_models = require_models
        self._profile = profile
        self._manifest = registry.manifest
        self._orchestrator = EkycOrchestrator(
            registry,
            max_video_frames=max_video_frames,
            max_face_match_frames=max_face_match_frames,
            replay_suspicious_threshold=replay_suspicious_threshold,
            camera_injection_suspicious_threshold=camera_injection_suspicious_threshold,
            face_match_threshold=face_match_threshold,
            face_match_consider_threshold=face_match_consider_threshold,
            passive_liveness_threshold=passive_liveness_threshold,
            passive_liveness_consider_threshold=passive_liveness_consider_threshold,
            visual_deepfake_threshold=visual_deepfake_threshold,
            face_quality_min_video_face_frames=face_quality_min_video_face_frames,
            face_quality_blur_threshold=face_quality_blur_threshold,
            face_quality_min_coverage=face_quality_min_coverage,
            face_quality_max_coverage=face_quality_max_coverage,
            face_quality_yaw_threshold=face_quality_yaw_threshold,
            face_quality_roll_threshold=face_quality_roll_threshold,
        )

    def readiness(self) -> dict[str, Any]:
        summary = self._manifest.summary()
        capabilities = self._registry.readiness()
        if not summary.manifest:
            return {
                "ready": not self._require_models,
                "artifact_ready": False,
                "pipeline_ready": False,
                "profile": self._profile,
                "manifest": False,
                "models": [],
                "invalid": ["manifest.json:missing"],
                "capabilities": capabilities,
            }
        artifact_ready = summary.artifact_ready
        return {
            "ready": artifact_ready if self._require_models else True,
            "artifact_ready": artifact_ready,
            "pipeline_ready": artifact_ready,
            "profile": self._profile,
            "manifest": True,
            "models": summary.model_ids,
            "invalid": summary.invalid,
            "capabilities": capabilities,
        }

    @classmethod
    def _collect_statuses(cls, value: Any) -> list[str]:
        # `attempts` carries its own per-try status vocabulary (COMPLETED,
        # TIMEOUT, INVALID_OUTPUT, UNAVAILABLE, FAILED) which is not the same
        # thing as the capability's own execution_status - e.g. a capability
        # that failed over from primary to secondary has one UNAVAILABLE/
        # FAILED attempt and one COMPLETED attempt, but the capability itself
        # fully succeeded (ADR-M0-002). Recursing into attempts here would
        # wrongly count that failed attempt against the overall rollup.
        if isinstance(value, dict):
            status = value.get("execution_status", value.get("status"))
            statuses = [str(status)] if status is not None else []
            for key, child in value.items():
                if key == "attempts":
                    continue
                statuses.extend(cls._collect_statuses(child))
            return statuses
        if isinstance(value, list):
            return [status for child in value for status in cls._collect_statuses(child)]
        return []

    @staticmethod
    def _execution_status(value: dict[str, Any]) -> str:
        # "DEFECT_DETECTED" (document_quality, face_quality) means the check
        # ran successfully and found a real defect - a correct result, not a
        # capability failure. Mapping it to the default "ERROR" branch would
        # make a working quality check indistinguishable from the capability
        # itself crashing (pre-existing bug in document_quality's contract
        # output, caught while wiring face_quality the same way).
        return {
            "OK": "COMPLETED",
            "DEFECT_DETECTED": "COMPLETED",
            "INCONCLUSIVE": "INCONCLUSIVE",
            "UNAVAILABLE": "UNAVAILABLE",
        }.get(str(value.get("status", "UNAVAILABLE")), "ERROR")

    @classmethod
    def _normalize_nested_statuses(cls, value: Any) -> Any:
        if isinstance(value, dict):
            normalized = {
                key: (child if key == "attempts" else cls._normalize_nested_statuses(child))
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
        attempts = value.get("attempts")
        if attempts:
            output["attempts"] = attempts
            if not output["reason_codes"]:
                derived = sorted(
                    {code for attempt in attempts for code in attempt.get("reason_codes", [])}
                )
                if derived:
                    output["reason_codes"] = derived
        return output

    @staticmethod
    def _decision_review_signal(decision: str) -> str:
        """Maps the domain's 3-way match/consider/failed decision (see
        app.domain.threshold_decisions) onto the ekyc-analysis/1.0 contract's
        review_signal vocabulary (docs/M0_CONTRACT_GOVERNANCE_BASELINE.md)."""
        return {
            "match": "NO_ADVERSE_SIGNAL",
            "consider": "INCONCLUSIVE",
            "failed": "ADVERSE_SIGNAL",
        }.get(decision, "INCONCLUSIVE")

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
            decision = str(value.get("decision", "failed"))
            return cls._base_output(
                value,
                review_signal=cls._decision_review_signal(decision),
                metrics={
                    "cosine_similarity": value.get("cosine_similarity"),
                    "score_direction": "HIGHER_IS_MORE_SIMILAR",
                },
                threshold={
                    "value": value.get("match_threshold"),
                    "consider_threshold": value.get("consider_threshold"),
                    "approval_status": "EVALUATION_ONLY",
                },
                details={
                    "sampled_frames": value.get("sampled_frames"),
                    "frames_with_face": value.get("frames_with_face"),
                    "matched_frames": value.get("matched_frames"),
                    "aggregation": value.get("aggregation"),
                },
                reason_codes=[str(code) for code in value.get("reason_codes", [])],
            )
        if name == "liveness":
            decision = str(value.get("decision", "failed"))
            return cls._base_output(
                value,
                review_signal=cls._decision_review_signal(decision),
                metrics={
                    "live_probability": value.get("live_probability"),
                    "score_direction": "HIGHER_IS_MORE_LIVE_LIKE",
                },
                threshold={
                    "value": value.get("threshold"),
                    "consider_threshold": value.get("consider_threshold"),
                    "approval_status": "EVALUATION_ONLY",
                },
                reason_codes=[str(code) for code in value.get("reason_codes", [])],
            )
        if name == "visual_deepfake":
            suspicious = value.get("suspicious") is True
            return cls._base_output(
                value,
                review_signal="ADVERSE_SIGNAL" if suspicious else "NO_ADVERSE_SIGNAL",
                metrics={
                    "manipulation_probability": value.get("manipulation_probability"),
                    "score_direction": "HIGHER_IS_MORE_SUSPICIOUS",
                },
                threshold={
                    "value": value.get("threshold"),
                    "approval_status": "EVALUATION_ONLY",
                },
                reason_codes=[str(code) for code in value.get("reason_codes", [])],
            )
        if name == "face_quality":
            defect_flags = value.get("defect_flags") or []
            return cls._base_output(
                value,
                review_signal="ADVERSE_SIGNAL" if defect_flags else "NO_ADVERSE_SIGNAL",
                details={
                    "sampled_frame_count": value.get("sampled_frame_count"),
                    "multi_face_frame_count": value.get("multi_face_frame_count"),
                    "frontal_frame_found": value.get("frontal_frame_found"),
                    "defect_flags": defect_flags,
                    "warnings": value.get("warnings", []),
                },
                reason_codes=[str(code) for code in value.get("reason_codes", [])],
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
                "ADVERSE_SIGNAL"
                if verdict == "fake"
                else "NO_ADVERSE_SIGNAL"
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
                reason_codes=["LIP_SYNC_SUSPICIOUS"] if signal == "ADVERSE_SIGNAL" else [],
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
                review_signal="ADVERSE_SIGNAL" if suspicious else "NO_ADVERSE_SIGNAL",
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
    def _summary_reason_codes(
        cls, capabilities: dict[str, Any], readiness: dict[str, Any], statuses: list[str]
    ) -> list[str]:
        """Session-level reason codes over the already-normalized capabilities
        tree - a pure function of (capabilities, readiness, statuses) so this
        is unit-testable without a full registry/evidence round-trip."""
        summary_reason_codes = ["TECHNICAL_DEMO_MANUAL_REVIEW"]
        if not readiness["artifact_ready"] or "UNAVAILABLE" in statuses:
            summary_reason_codes.append("MODEL_UNAVAILABLE")
        if "INCONCLUSIVE" in statuses:
            summary_reason_codes.append("AI_RESULT_INCONCLUSIVE")
        for capability, reason in (
            ("replay_attack", "REPLAY_ATTACK_SUSPECTED"),
            ("camera_injection", "CAMERA_INJECTION_SUSPECTED"),
            ("lip_sync", "LIP_SYNC_SUSPICIOUS"),
            ("visual_deepfake", "VISUAL_DEEPFAKE_SUSPECTED"),
            ("face_match", "FACE_MATCH_ADVERSE_SIGNAL"),
            ("liveness", "PASSIVE_LIVENESS_ADVERSE_SIGNAL"),
            ("face_quality", "FACE_QUALITY_DEFECT_DETECTED"),
        ):
            signal = capabilities.get(capability, {})
            if isinstance(signal, dict) and signal.get("review_signal") == "ADVERSE_SIGNAL":
                summary_reason_codes.append(reason)
        voice_challenge_signal = capabilities.get("voice_challenge", {})
        if (
            isinstance(voice_challenge_signal, dict)
            and voice_challenge_signal.get("review_signal") == "CHALLENGE_MISMATCH"
        ):
            summary_reason_codes.append("VOICE_CHALLENGE_MISMATCH")
        active_liveness = capabilities.get("active_liveness", {})
        if (
            isinstance(active_liveness, dict)
            and active_liveness.get("review_signal") == "CHALLENGE_INCOMPLETE"
        ):
            summary_reason_codes.append("ACTIVE_LIVENESS_SEQUENCE_INCOMPLETE")
        # document_layout going UNAVAILABLE already trips the generic
        # MODEL_UNAVAILABLE check above (via _collect_statuses recursing into
        # every nested execution_status), but that's the same catch-all any
        # transient capability hiccup anywhere produces. Called out
        # separately here because losing this specific model is losing all
        # CCCD structured-field extraction (not just the document_quality
        # corners check that also depends on it) - worth a name a reviewer
        # can actually recognize, not just "something, somewhere failed".
        ocr_documents = capabilities.get("ocr", {})
        documents = ocr_documents.get("documents", {}) if isinstance(ocr_documents, dict) else {}
        if isinstance(documents, dict) and any(
            isinstance(document, dict)
            and isinstance(document.get("details", {}).get("layout"), dict)
            and document["details"]["layout"].get("execution_status") == "UNAVAILABLE"
            for document in documents.values()
        ):
            summary_reason_codes.append("DOCUMENT_LAYOUT_UNAVAILABLE")

        def _expired(document: Any) -> bool:
            if not isinstance(document, dict) or not isinstance(document.get("details"), dict):
                return False
            details = document["details"]
            return any(
                isinstance(details.get(key), dict) and details[key].get("expired") is True
                for key in ("layout", "mrz")
            )

        if isinstance(documents, dict) and any(
            _expired(document) for document in documents.values()
        ):
            summary_reason_codes.append("DOCUMENT_EXPIRED")
        return summary_reason_codes

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
                        {key: result[key] for key in ("layout", "mrz", "quality") if key in result}
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
        results = self._orchestrator.analyze_ocr(document_type, evidence)
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
            if isinstance(result.get("layout"), dict):
                document["layout"] = self._normalize_nested_statuses(result["layout"])
            if isinstance(result.get("quality"), dict):
                document["quality"] = self._normalize_nested_statuses(result["quality"])
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
        capabilities = self._orchestrator.analyze(document_type, voice_challenge, evidence)
        capabilities = self.normalize_capabilities(capabilities)
        statuses = self._collect_statuses(capabilities)
        summary_reason_codes = self._summary_reason_codes(capabilities, readiness, statuses)

        if not readiness["artifact_ready"] or "UNAVAILABLE" in statuses:
            if "COMPLETED" in statuses:
                top_execution_status = "PARTIAL"
            else:
                top_execution_status = "UNAVAILABLE"
        else:
            top_execution_status = "COMPLETED"
        top_review_signal = (
            "MODEL_UNAVAILABLE"
            if top_execution_status == "UNAVAILABLE"
            else "MANUAL_REVIEW_REQUIRED"
        )

        return {
            "contract_version": "ekyc-analysis/1.0",
            "session_id": str(session_id),
            "pipeline": "offline-technical-demo",
            "profile": self._profile,
            "execution_status": top_execution_status,
            "review_signal": top_review_signal,
            "model_readiness": readiness,
            "evidence_types": sorted(item.evidence_type for item in evidence),
            "capabilities": capabilities,
            "summary_reason_codes": summary_reason_codes,
            "created_at": datetime.now(UTC).isoformat(),
        }
