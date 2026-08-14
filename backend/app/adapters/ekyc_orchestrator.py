from __future__ import annotations

import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from ai_modules.ekyc.active_liveness import estimate_head_yaw
from ai_modules.ekyc.errors import InvalidEvidenceError
from ai_modules.ekyc.media import decode_image, media_suffix, video_frames, video_metadata
from app.adapters.capability_registry import CapabilityRegistry, CapabilityUnavailableError
from app.domain.capability_ports import (
    ActiveLivenessRequest,
    ActiveLivenessResult,
    Attempt,
    CameraInjectionRequest,
    CapabilityName,
    DocumentLayoutRequest,
    DocumentOcrRequest,
    DocumentQualityRequest,
    FaceDetectionRequest,
    FaceDetectionResult,
    FaceMatchingRequest,
    LipSyncRequest,
    PassiveLivenessRequest,
    PassportMrzRequest,
    ReplayAttackRequest,
    ReplayAttackResult,
    VisualDeepfakeRequest,
    VoiceChallengeRequest,
)
from app.domain.document_fields import parse_layout_fields
from app.domain.face_matching import select_face_match_candidates


class EkycOrchestrator:
    """Business workflow: frame extraction, temp-file handling, capability
    error isolation, and request-building for the submitted evidence.

    Per ADR-M0-001 this class never constructs a concrete model engine - it
    only builds capability requests and calls `CapabilityRegistry`, which is
    the composition root's job to wire up. It replaces the pre-M2 pipeline,
    which built engines directly and therefore could not be swapped by config.
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
        *,
        max_video_frames: int = 36,
        max_face_match_frames: int = 12,
        replay_suspicious_threshold: float = 0.62,
        camera_injection_suspicious_threshold: float = 0.60,
        face_match_threshold: float = 0.45,
        face_match_consider_threshold: float = 0.30,
        passive_liveness_threshold: float = 0.65,
        passive_liveness_consider_threshold: float = 0.45,
        visual_deepfake_threshold: float = 0.68,
    ) -> None:
        self._registry = registry
        self._max_video_frames = max(1, max_video_frames)
        self._max_face_match_frames = max(1, max_face_match_frames)
        self._replay_suspicious_threshold = replay_suspicious_threshold
        self._camera_injection_suspicious_threshold = camera_injection_suspicious_threshold
        self._face_match_threshold = face_match_threshold
        self._face_match_consider_threshold = face_match_consider_threshold
        self._passive_liveness_threshold = passive_liveness_threshold
        self._passive_liveness_consider_threshold = passive_liveness_consider_threshold
        self._visual_deepfake_threshold = visual_deepfake_threshold

    @staticmethod
    def _failure_from_attempts(attempts: list[Attempt]) -> dict[str, Any]:
        inconclusive = bool(attempts) and attempts[-1].status == "INVALID_OUTPUT"
        return {
            "status": "INCONCLUSIVE" if inconclusive else "UNAVAILABLE",
            "attempts": [attempt.to_dict() for attempt in attempts],
        }

    def _to_output(self, result: Any, attempts: list[Attempt]) -> dict[str, Any]:
        """Serialize a typed provider result (or synthesize a failure dict
        from `attempts` when every provider failed) into the plain-dict shape
        the analysis contract/reviewer surface expects."""
        if result is None:
            return self._failure_from_attempts(attempts)
        enriched = asdict(result)
        enriched["attempts"] = [attempt.to_dict() for attempt in attempts]
        return enriched

    def _run(self, capability: CapabilityName, request: Any) -> dict[str, Any]:
        result, attempts = self._registry.run(capability, request)
        return self._to_output(result, attempts)

    def _run_document_quality(
        self, payload: bytes, *, layout_corners: dict[str, list[float]] | None = None
    ) -> dict[str, Any]:
        # Unlike document_ocr/document_layout (which take raw bytes and only
        # decode inside the real provider, so a not-ready/faked provider
        # never touches undecodable bytes), DocumentQualityRequest takes a
        # pre-decoded image (see app.api's evidence-upload endpoint, the
        # other caller) - so this decode must be guarded here itself,
        # matching that endpoint's try/except InvalidEvidenceError.
        try:
            image = decode_image(payload)
        except InvalidEvidenceError:
            return {"status": "UNAVAILABLE", "error_type": "InvalidEvidenceError"}
        return self._run(
            "document_quality", DocumentQualityRequest(image, layout_corners=layout_corners)
        )

    def _run_document_layout(self, payload: bytes) -> dict[str, Any]:
        """document_layout's raw per-field OCR text still carries the printed
        CCCD label (see ai_modules.ekyc.document_layout) - clean it into
        `parsed_fields` via the rule-based (no-LLM) domain parser."""
        layout_result = self._run("document_layout", DocumentLayoutRequest(payload))
        layout_result["parsed_fields"] = parse_layout_fields(layout_result.get("fields", {}))
        return layout_result

    def analyze_ocr(self, document_type: str, evidence: list[Any]) -> dict[str, Any]:
        """Run only OCR (+ MRZ for passports) for an authorized, transient
        technical-demo disclosure. Unlike `analyze()`, raw text lines stay in
        the result - this is the explicit, reviewer-triggered decrypt path."""
        by_type = {entry.evidence_type: entry for entry in evidence}
        passport = document_type == "PASSPORT_TD3"
        document_types = ["PASSPORT_PAGE"] if passport else ["DOCUMENT_FRONT", "DOCUMENT_BACK"]
        results: dict[str, Any] = {}
        for evidence_type in document_types:
            entry = by_type.get(evidence_type)
            if entry is None:
                continue
            document_result = self._run("document_ocr", DocumentOcrRequest(entry.payload))
            if passport:
                document_result["quality"] = self._run_document_quality(entry.payload)
                lines = document_result.get("lines", [])
                document_result["mrz"] = self._run("passport_mrz", PassportMrzRequest(lines=lines))
            else:
                # Layout runs first so its YOLO corner-marker boxes can feed
                # the quality check's corners detection - see
                # _run_document_quality's layout_corners and
                # ai_modules.ekyc.document_quality's priority over its own
                # contour-based fallback.
                document_result["layout"] = self._run_document_layout(entry.payload)
                document_result["quality"] = self._run_document_quality(
                    entry.payload, layout_corners=document_result["layout"].get("corners")
                )
            results[evidence_type.lower()] = document_result
        return results

    def analyze(
        self,
        document_type: str,
        voice_challenge: str,
        evidence: list[Any],
    ) -> dict[str, Any]:
        by_type = {entry.evidence_type: entry for entry in evidence}
        passport = document_type == "PASSPORT_TD3"
        document_types = ["PASSPORT_PAGE"] if passport else ["DOCUMENT_FRONT", "DOCUMENT_BACK"]

        ocr_results: dict[str, Any] = {}
        for evidence_type in document_types:
            entry = by_type[evidence_type]
            document_result = self._run("document_ocr", DocumentOcrRequest(entry.payload))
            lines = document_result.pop("lines", [])
            if passport:
                document_result["quality"] = self._run_document_quality(entry.payload)
                document_result["mrz"] = self._run("passport_mrz", PassportMrzRequest(lines=lines))
            else:
                # Layout first so quality's corners check can use its YOLO
                # corner-marker boxes - see analyze_ocr's identical ordering.
                document_result["layout"] = self._run_document_layout(entry.payload)
                document_result["quality"] = self._run_document_quality(
                    entry.payload, layout_corners=document_result["layout"].get("corners")
                )
            ocr_results[evidence_type.lower()] = document_result

        video = by_type["SELFIE_VIDEO"]
        temporary_path: Path | None = None
        face_result: dict[str, Any]
        liveness_result: dict[str, Any]
        active_liveness_result: dict[str, Any]
        deepfake_result: dict[str, Any]
        voice_result: dict[str, Any]
        lipsync_result: dict[str, Any]
        replay_result: dict[str, Any]
        camera_injection_result: dict[str, Any]
        try:
            with tempfile.NamedTemporaryFile(
                suffix=media_suffix(video.content_type), delete=False
            ) as stream:
                stream.write(video.payload)
                temporary_path = Path(stream.name)
            frames = video_frames(temporary_path, self._max_video_frames)
            metadata = video_metadata(temporary_path)
            document_entry = by_type[document_types[0]]
            document_image = decode_image(document_entry.payload)

            # face_detection is called once per frame (up to max_video_frames);
            # it goes through registry.resolve() rather than registry.run() so
            # per-frame calls don't each produce their own attempts entry -
            # see CapabilityRegistry.resolve()'s docstring.
            face_detector = self._registry.resolve("face_detection")
            document_face = face_detector.run(FaceDetectionRequest(document_image))
            live_candidates: list[tuple[np.ndarray, FaceDetectionResult]] = []
            for frame in frames:
                try:
                    live_candidates.append((frame, face_detector.run(FaceDetectionRequest(frame))))
                except InvalidEvidenceError:
                    continue
            if not live_candidates:
                raise InvalidEvidenceError("No face detected in selfie video")

            yaw_samples = [
                estimate_head_yaw(candidate.landmarks) for _, candidate in live_candidates
            ]
            active_liveness_raw: ActiveLivenessResult | None
            active_liveness_raw, active_liveness_attempts = self._registry.run(
                "active_liveness", ActiveLivenessRequest(yaw_samples)
            )
            active_liveness_result = self._to_output(active_liveness_raw, active_liveness_attempts)
            replay_raw: ReplayAttackResult | None
            replay_raw, replay_attempts = self._registry.run(
                "replay_attack",
                ReplayAttackRequest(
                    frames=frames, suspicious_threshold=self._replay_suspicious_threshold
                ),
            )
            replay_result = self._to_output(replay_raw, replay_attempts)
            camera_injection_result = self._run(
                "camera_injection",
                CameraInjectionRequest(
                    frames=frames,
                    fps=metadata["fps"],
                    frame_count=(
                        int(metadata["frame_count"])
                        if metadata["frame_count"] is not None
                        else None
                    ),
                    duration_ms=metadata["duration_ms"],
                    active_liveness=active_liveness_raw,
                    replay=replay_raw,
                    suspicious_threshold=self._camera_injection_suspicious_threshold,
                ),
            )
            face_result = self._run(
                "face_matching",
                FaceMatchingRequest(
                    document_image=document_image,
                    document_face=document_face,
                    live_candidates=live_candidates,
                    max_frames=self._max_face_match_frames,
                    sampled_frame_count=len(frames),
                    match_threshold=self._face_match_threshold,
                    consider_threshold=self._face_match_consider_threshold,
                ),
            )
            live_image, live_face = select_face_match_candidates(
                live_candidates, self._max_face_match_frames
            )[0]
            liveness_result = self._run(
                "passive_liveness",
                PassiveLivenessRequest(
                    image=live_image,
                    bbox=live_face.bbox,
                    live_threshold=self._passive_liveness_threshold,
                    consider_threshold=self._passive_liveness_consider_threshold,
                ),
            )
            deepfake_result = self._run(
                "visual_deepfake",
                VisualDeepfakeRequest(
                    image=live_image,
                    bbox=live_face.bbox,
                    suspicious_threshold=self._visual_deepfake_threshold,
                ),
            )
        except CapabilityUnavailableError as exc:
            failure = {"status": "UNAVAILABLE", "reason": exc.reason}
            face_result = failure
            liveness_result = dict(failure)
            active_liveness_result = dict(failure)
            deepfake_result = dict(failure)
            replay_result = dict(failure)
            camera_injection_result = dict(failure)
        except Exception as exc:  # capability isolation, mirrors previous pipeline behavior
            status = "INCONCLUSIVE" if isinstance(exc, InvalidEvidenceError) else "UNAVAILABLE"
            failure = {"status": status, "error_type": type(exc).__name__}
            face_result = failure
            liveness_result = dict(failure)
            active_liveness_result = dict(failure)
            deepfake_result = dict(failure)
            replay_result = dict(failure)
            camera_injection_result = dict(failure)

        if temporary_path is None:
            voice_result = {"status": "UNAVAILABLE", "error_type": "VideoTemporaryFileError"}
            lipsync_result = dict(voice_result)
        else:
            voice_result = self._run(
                "voice_challenge",
                VoiceChallengeRequest(media_path=temporary_path, challenge=voice_challenge),
            )
            lipsync_result = self._run(
                "lip_sync",
                LipSyncRequest(media_path=temporary_path, content_type=video.content_type),
            )
            temporary_path.unlink(missing_ok=True)

        return {
            "ocr": ocr_results,
            "face_match": face_result,
            "liveness": liveness_result,
            "active_liveness": active_liveness_result,
            "replay_attack": replay_result,
            "camera_injection": camera_injection_result,
            "visual_deepfake": deepfake_result,
            "voice_challenge": voice_result,
            "lip_sync": lipsync_result,
        }
