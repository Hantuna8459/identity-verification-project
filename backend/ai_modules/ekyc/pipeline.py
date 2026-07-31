from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from ai_modules.ekyc.runtime import (
    CccdLayoutOcr,
    InvalidEvidenceError,
    LocalOcr,
    OnnxSignals,
    ScrfdArcFace,
    VoiceVerifier,
    call_lipsync,
    decode_image,
    estimate_head_yaw,
    inspect_head_turn_sequence,
    media_suffix,
    video_frames,
)


class TechnicalDemoPipeline:
    """Offline capability orchestration; it never makes an identity decision."""

    def __init__(
        self,
        model_dir: Path,
        *,
        device: str = "cpu",
        lipsync_url: str | None = None,
        max_video_frames: int = 12,
    ) -> None:
        self._model_dir = model_dir
        self._device = device
        self._lipsync_url = lipsync_url
        self._max_video_frames = max(1, max_video_frames)
        self._ocr: LocalOcr | None = None
        self._layout: CccdLayoutOcr | None = None
        self._face: ScrfdArcFace | None = None
        self._signals: OnnxSignals | None = None
        self._voice: VoiceVerifier | None = None

    @staticmethod
    def _failure(exc: Exception) -> dict[str, Any]:
        status = "INCONCLUSIVE" if isinstance(exc, InvalidEvidenceError) else "UNAVAILABLE"
        return {"status": status, "error_type": type(exc).__name__}

    def _ocr_engine(self) -> LocalOcr:
        if self._ocr is None:
            self._ocr = LocalOcr(self._model_dir)
        return self._ocr

    def _layout_engine(self) -> CccdLayoutOcr:
        if self._layout is None:
            self._layout = CccdLayoutOcr(self._model_dir)
        return self._layout

    def _face_engine(self) -> ScrfdArcFace:
        if self._face is None:
            self._face = ScrfdArcFace(self._model_dir)
        return self._face

    def _signal_engine(self) -> OnnxSignals:
        if self._signals is None:
            self._signals = OnnxSignals(self._model_dir)
        return self._signals

    def _voice_engine(self) -> VoiceVerifier:
        if self._voice is None:
            self._voice = VoiceVerifier(self._model_dir, self._device)
        return self._voice

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
            try:
                document_result = self._ocr_engine().inspect_document(
                    by_type[evidence_type].payload, passport=passport
                )
                if not passport:
                    document_result["layout"] = self._layout_engine().inspect(
                        by_type[evidence_type].payload, self._ocr_engine()
                    )
                ocr_results[evidence_type.lower()] = document_result
            except Exception as exc:  # capability isolation
                ocr_results[evidence_type.lower()] = self._failure(exc)

        video = by_type["SELFIE_VIDEO"]
        temporary_path: Path | None = None
        face_result: dict[str, Any]
        liveness_result: dict[str, Any]
        active_liveness_result: dict[str, Any]
        deepfake_result: dict[str, Any]
        voice_result: dict[str, Any]
        lipsync_result: dict[str, Any]
        try:
            with tempfile.NamedTemporaryFile(
                suffix=media_suffix(video.content_type), delete=False
            ) as stream:
                stream.write(video.payload)
                temporary_path = Path(stream.name)
            frames = video_frames(temporary_path, self._max_video_frames)
            document_entry = by_type[document_types[0]]
            document_image = decode_image(document_entry.payload)
            face_engine = self._face_engine()
            document_face = face_engine.best_face(document_image)
            live_candidates = []
            for frame in frames:
                try:
                    live_candidates.append((frame, face_engine.best_face(frame)))
                except InvalidEvidenceError:
                    continue
            if not live_candidates:
                raise InvalidEvidenceError("No face detected in selfie video")
            yaw_samples = [
                estimate_head_yaw(np.asarray(candidate["landmarks"]))
                for _, candidate in live_candidates
            ]
            active_liveness_result = inspect_head_turn_sequence(yaw_samples)
            live_image, live_face = max(
                live_candidates,
                key=lambda item: float(item[1]["score"]),
            )
            document_embedding = face_engine.embedding(
                document_image, np.asarray(document_face["landmarks"])
            )
            live_embedding = face_engine.embedding(live_image, np.asarray(live_face["landmarks"]))
            similarity = float(np.dot(document_embedding, live_embedding))
            face_result = {
                "status": "OK",
                "engine": "insightface-buffalo_l/SCRFD-10G+ArcFace-R50",
                "cosine_similarity": round(similarity, 6),
                "sampled_frames": len(frames),
                "frames_with_face": len(live_candidates),
            }
            try:
                score = self._signal_engine().liveness(live_image, np.asarray(live_face["bbox"]))
                liveness_result = {
                    "status": "OK",
                    "engine": "MiniFASNetV2",
                    "live_probability": round(score, 6),
                }
            except Exception as exc:
                liveness_result = self._failure(exc)
            try:
                probability = self._signal_engine().deepfake(
                    live_image, np.asarray(live_face["bbox"])
                )
                deepfake_result = {
                    "status": "OK",
                    "engine": "Deep-Fake-Detector-v2-Q4",
                    "manipulation_probability": round(probability, 6),
                }
            except Exception as exc:
                deepfake_result = self._failure(exc)
        except Exception as exc:
            failure = self._failure(exc)
            face_result = failure
            liveness_result = dict(failure)
            active_liveness_result = dict(failure)
            deepfake_result = dict(failure)

        if temporary_path is None:
            voice_result = {"status": "UNAVAILABLE", "error_type": "VideoTemporaryFileError"}
            lipsync_result = dict(voice_result)
        else:
            try:
                voice_result = self._voice_engine().verify(temporary_path, voice_challenge)
            except Exception as exc:
                voice_result = self._failure(exc)
            if self._lipsync_url:
                try:
                    lipsync_result = call_lipsync(
                        self._lipsync_url, temporary_path, video.content_type
                    )
                except Exception as exc:
                    lipsync_result = self._failure(exc)
            else:
                lipsync_result = {"status": "UNAVAILABLE", "reason": "SERVICE_NOT_CONFIGURED"}
            temporary_path.unlink(missing_ok=True)

        return {
            "ocr": ocr_results,
            "face_match": face_result,
            "liveness": liveness_result,
            "active_liveness": active_liveness_result,
            "visual_deepfake": deepfake_result,
            "voice_challenge": voice_result,
            "lip_sync": lipsync_result,
        }
