from __future__ import annotations

from dataclasses import asdict
from typing import Any

import numpy as np

from ai_modules.ekyc.active_liveness import inspect_head_turn_sequence
from ai_modules.ekyc.camera_injection import inspect_camera_injection
from ai_modules.ekyc.document_layout import CccdLayoutOcr
from ai_modules.ekyc.document_ocr import LocalOcr, VietOcr
from ai_modules.ekyc.document_quality import inspect_document_quality
from ai_modules.ekyc.face_detection import ScrfdFaceDetector
from ai_modules.ekyc.face_embedding import ArcFaceEmbedder
from ai_modules.ekyc.face_quality import aggregate_face_quality, assess_face_frame
from ai_modules.ekyc.media import call_lipsync
from ai_modules.ekyc.passive_liveness import MiniFasNetEngine
from ai_modules.ekyc.passport_mrz import inspect_td3
from ai_modules.ekyc.replay_attack import inspect_replay_attack
from ai_modules.ekyc.visual_deepfake import DeepfakeEngine
from ai_modules.ekyc.voice_challenge import VoiceVerifier
from app.adapters.capability_registry import CapabilityRegistry, ProviderRegistration
from app.adapters.manifest import ManifestReader
from app.core.capability_config import (
    CAPABILITY_PROVIDER_CONFIG_VERSION,
    build_provider_chains,
)
from app.core.config import Settings
from app.domain.capability_ports import (
    ActiveLivenessRequest,
    ActiveLivenessResult,
    CameraInjectionRequest,
    CameraInjectionResult,
    DocumentLayoutRequest,
    DocumentLayoutResult,
    DocumentOcrRequest,
    DocumentOcrResult,
    DocumentQualityRequest,
    DocumentQualityResult,
    FaceDetectionRequest,
    FaceDetectionResult,
    FaceEmbeddingRequest,
    FaceMatchingRequest,
    FaceMatchingResult,
    FaceQualityRequest,
    FaceQualityResult,
    LipSyncRequest,
    LipSyncResult,
    PassiveLivenessRequest,
    PassiveLivenessResult,
    PassportMrzRequest,
    PassportMrzResult,
    ReplayAttackRequest,
    ReplayAttackResult,
    VisualDeepfakeRequest,
    VisualDeepfakeResult,
    VoiceChallengeRequest,
    VoiceChallengeResult,
)
from app.domain.face_matching import aggregate_face_similarities, select_face_match_candidates
from app.domain.threshold_decisions import (
    decide_face_match,
    decide_passive_liveness,
    decide_visual_deepfake,
)

ADAPTER_SPEC_VERSION = "ekyc-provider-adapter/1"


class RapidOcrDocumentProvider:
    provider_id = "rapidocr-ppocrv6-small"
    model_id: str | None = "rapidocr-ppocrv6-small"
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def __init__(self, engine: LocalOcr) -> None:
        self._engine = engine

    def run(self, request: DocumentOcrRequest) -> DocumentOcrResult:
        raw = self._engine.inspect_document(request.payload)
        return DocumentOcrResult(
            status=raw["status"],
            engine=raw["engine"],
            line_count=raw["line_count"],
            mean_confidence=raw["mean_confidence"],
            lines=raw["lines"],
        )


class VietOcrDocumentProvider:
    provider_id = "vietocr-vgg-transformer"
    model_id: str | None = "vietocr-vgg-transformer"
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def __init__(self, engine: VietOcr) -> None:
        self._engine = engine

    def run(self, request: DocumentOcrRequest) -> DocumentOcrResult:
        raw = self._engine.inspect_document(request.payload)
        return DocumentOcrResult(
            status=raw["status"],
            engine=raw["engine"],
            line_count=raw["line_count"],
            mean_confidence=raw["mean_confidence"],
            lines=raw["lines"],
        )


class YoloCccdLayoutProvider:
    provider_id = "cccd-layout-yolov11"
    model_id: str | None = "cccd-layout-yolov11"
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def __init__(self, engine: CccdLayoutOcr, ocr: LocalOcr | VietOcr) -> None:
        self._engine = engine
        self._ocr = ocr

    def run(self, request: DocumentLayoutRequest) -> DocumentLayoutResult:
        region_ocr_engine_name = "VietOCR" if isinstance(self._ocr, VietOcr) else "RapidOCR"
        raw = self._engine.inspect(
            request.payload, self._ocr.read_array, region_ocr_engine_name=region_ocr_engine_name
        )
        return DocumentLayoutResult(
            status=raw["status"],
            engine=raw["engine"],
            region_count=raw["region_count"],
            class_counts=raw["class_counts"],
            ocr_line_count=raw["ocr_line_count"],
            mean_ocr_confidence=raw.get("mean_ocr_confidence"),
            fields=raw.get("fields", {}),
            corners=raw.get("corners", {}),
        )


class IcaoTd3MrzProvider:
    provider_id = "icao-td3-rules"
    model_id: str | None = None
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def run(self, request: PassportMrzRequest) -> PassportMrzResult:
        raw = inspect_td3(request.lines)
        return PassportMrzResult(
            status=raw["status"],
            format=raw["format"],
            mrz_detected=raw["mrz_detected"],
            all_check_digits_valid=raw["all_check_digits_valid"],
            line_lengths=raw.get("line_lengths"),
            check_digits=raw.get("check_digits"),
        )


class ScrfdFaceDetectionProvider:
    provider_id = "insightface-buffalo-l-scrfd"
    model_id: str | None = "insightface-buffalo-l"
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def __init__(self, engine: ScrfdFaceDetector) -> None:
        self._engine = engine

    def run(self, request: FaceDetectionRequest) -> FaceDetectionResult:
        raw = self._engine.best_face(request.image)
        return FaceDetectionResult(
            score=float(raw["score"]),
            bbox=np.asarray(raw["bbox"]),
            landmarks=np.asarray(raw["landmarks"]),
            face_count=int(raw.get("face_count", 1)),
        )


class ArcFaceEmbeddingProvider:
    provider_id = "insightface-buffalo-l-arcface"
    model_id: str | None = "insightface-buffalo-l"
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def __init__(self, engine: ArcFaceEmbedder) -> None:
        self._engine = engine

    def run(self, request: FaceEmbeddingRequest) -> np.ndarray:
        return self._engine.embedding(request.image, request.landmarks)


class MedianFaceMatchingProvider:
    """Aggregates document-vs-selfie similarity across sampled frames.

    Depends on a face_embedding provider instance (resolved once by the
    composition root via `CapabilityRegistry.resolve("face_embedding")`) -
    face_detection has already run for every candidate frame by the time this
    is called, so only embedding + aggregation happens here.
    """

    provider_id = "insightface-buffalo-l-median"
    model_id: str | None = "insightface-buffalo-l"
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def __init__(self, embedder: ArcFaceEmbeddingProvider) -> None:
        self._embedder = embedder

    def run(self, request: FaceMatchingRequest) -> FaceMatchingResult:
        candidates = select_face_match_candidates(request.live_candidates, request.max_frames)
        document_embedding = self._embedder.run(
            FaceEmbeddingRequest(request.document_image, request.document_face.landmarks)
        )
        similarities: list[float] = []
        frames_with_embedding = 0
        for candidate_image, candidate_face in candidates:
            try:
                live_embedding = self._embedder.run(
                    FaceEmbeddingRequest(candidate_image, candidate_face.landmarks)
                )
            except Exception:  # capability isolation for a single frame
                continue
            frames_with_embedding += 1
            similarities.append(float(np.dot(document_embedding, live_embedding)))
        similarity = aggregate_face_similarities(similarities)
        decision, reason_codes = decide_face_match(
            similarity, request.match_threshold, request.consider_threshold
        )
        return FaceMatchingResult(
            status="OK",
            engine="insightface-buffalo_l/SCRFD-10G+ArcFace-R50",
            cosine_similarity=round(similarity, 6),
            sampled_frames=request.sampled_frame_count,
            frames_with_face=len(request.live_candidates),
            matched_frames=frames_with_embedding,
            aggregation="MEDIAN",
            match_threshold=request.match_threshold,
            consider_threshold=request.consider_threshold,
            decision=decision,
            reason_codes=reason_codes,
        )


class HeuristicFaceQualityProvider:
    """Reuses the same live_candidates face_matching already has (face
    detection already ran once per frame by the time this is called) -
    no model of its own, same pattern as HeuristicDocumentQualityProvider."""

    provider_id = "heuristic-face-quality-v1"
    model_id: str | None = None
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def run(self, request: FaceQualityRequest) -> FaceQualityResult:
        frame_assessments = [
            assess_face_frame(image, face.bbox, face.landmarks, face.face_count)
            for image, face in request.live_candidates
        ]
        raw = aggregate_face_quality(
            frame_assessments,
            min_video_face_frames=request.min_video_face_frames,
            blur_threshold=request.blur_threshold,
            min_coverage=request.min_coverage,
            max_coverage=request.max_coverage,
            yaw_threshold=request.yaw_threshold,
            roll_threshold=request.roll_threshold,
        )
        return FaceQualityResult(
            status=raw["status"],
            engine=raw["engine"],
            sampled_frame_count=raw["sampled_frame_count"],
            multi_face_frame_count=raw["multi_face_frame_count"],
            frontal_frame_found=raw["frontal_frame_found"],
            defect_flags=raw["defect_flags"],
            reason_codes=raw["reason_codes"],
            warnings=raw["warnings"],
        )


class MiniFasNetLivenessProvider:
    provider_id = "minifasnet-v2"
    model_id: str | None = "minifasnet-v2"
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def __init__(self, engine: MiniFasNetEngine) -> None:
        self._engine = engine

    def run(self, request: PassiveLivenessRequest) -> PassiveLivenessResult:
        score = self._engine.liveness(request.image, request.bbox)
        decision, reason_codes = decide_passive_liveness(
            score, request.live_threshold, request.consider_threshold
        )
        return PassiveLivenessResult(
            status="OK",
            engine="MiniFASNetV2",
            live_probability=round(score, 6),
            threshold=request.live_threshold,
            consider_threshold=request.consider_threshold,
            decision=decision,
            reason_codes=reason_codes,
        )


class HeadPoseActiveLivenessProvider:
    provider_id = "scrfd-head-pose-rules"
    model_id: str | None = None
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def run(self, request: ActiveLivenessRequest) -> ActiveLivenessResult:
        raw = inspect_head_turn_sequence(request.yaw_samples)
        return ActiveLivenessResult(
            status=raw["status"],
            engine=raw["engine"],
            sequence_complete=raw["sequence_complete"],
            completed_step_count=raw["completed_step_count"],
            required_step_count=raw["required_step_count"],
            sampled_pose_count=raw["sampled_pose_count"],
            reason=raw.get("reason"),
        )


class DeepfakeDetectorProvider:
    provider_id = "deepfake-detector-v2-q4"
    model_id: str | None = "deepfake-detector-v2-q4"
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def __init__(self, engine: DeepfakeEngine) -> None:
        self._engine = engine

    def run(self, request: VisualDeepfakeRequest) -> VisualDeepfakeResult:
        probability = self._engine.deepfake(request.image, request.bbox)
        suspicious, reason_codes = decide_visual_deepfake(probability, request.suspicious_threshold)
        return VisualDeepfakeResult(
            status="OK",
            engine="Deep-Fake-Detector-v2-Q4",
            manipulation_probability=round(probability, 6),
            threshold=request.suspicious_threshold,
            suspicious=suspicious,
            reason_codes=reason_codes,
        )


class VoskVoiceChallengeProvider:
    provider_id = "vosk-small-vn-0.4"
    model_id: str | None = "vosk-small-vn-0.4"
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def __init__(self, engine: VoiceVerifier) -> None:
        self._engine = engine

    def run(self, request: VoiceChallengeRequest) -> VoiceChallengeResult:
        raw = self._engine.verify(request.media_path, request.challenge)
        return VoiceChallengeResult(
            status=raw["status"],
            engine=raw["engine"],
            challenge_length=raw["challenge_length"],
            recognized_digit_count=raw["recognized_digit_count"],
            similarity=raw["similarity"],
        )


class HttpLipSyncProvider:
    provider_id = "syncnet-s3fd-http"
    model_id: str | None = "syncnet-v2"
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def __init__(self, lipsync_url: str) -> None:
        self._lipsync_url = lipsync_url

    def run(self, request: LipSyncRequest) -> LipSyncResult:
        raw = call_lipsync(self._lipsync_url, request.media_path, request.content_type)
        return LipSyncResult(
            status=raw["status"],
            engine=raw["engine"],
            verdict=raw.get("verdict"),
            confidence=raw.get("confidence"),
            manipulation_probability=raw.get("manipulation_probability"),
        )


class HeuristicDocumentQualityProvider:
    provider_id = "heuristic-document-quality-v1"
    model_id: str | None = None
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def run(self, request: DocumentQualityRequest) -> DocumentQualityResult:
        raw = inspect_document_quality(request.image, layout_corners=request.layout_corners)
        return DocumentQualityResult(
            status=raw["status"],
            engine=raw["engine"],
            blur_score=raw["blur_score"],
            glare_ratio=raw["glare_ratio"],
            brightness_mean=raw["brightness_mean"],
            contrast_score=raw["contrast_score"],
            corners_detected=raw["corners_detected"],
            corner_coverage_ratio=raw["corner_coverage_ratio"],
            corner_source=raw["corner_source"],
            screenshot_score=raw["screenshot_score"],
            defect_flags=raw["defect_flags"],
            reason_codes=raw["reason_codes"],
            warnings=raw["warnings"],
        )


class HeuristicReplayProvider:
    provider_id = "heuristic-replay-v1"
    model_id: str | None = None
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def run(self, request: ReplayAttackRequest) -> ReplayAttackResult:
        raw = inspect_replay_attack(
            request.frames, suspicious_threshold=request.suspicious_threshold
        )
        return ReplayAttackResult(
            status=raw["status"],
            engine=raw["engine"],
            score=raw["score"],
            threshold=raw["threshold"],
            confirmed=raw["confirmed"],
            duplicate_pairs=raw["duplicate_pairs"],
            warnings=raw["warnings"],
            suspicious=raw.get("suspicious", False),
            moire_score=raw.get("moire_score"),
            flicker_score=raw.get("flicker_score"),
            duplication_score=raw.get("duplication_score"),
            face_motion_score=raw.get("face_motion_score"),
            reason_codes=raw.get("reason_codes", []),
            reason=raw.get("reason"),
        )


class HeuristicCameraInjectionProvider:
    provider_id = "heuristic-camera-injection-v1"
    model_id: str | None = None
    adapter_spec_version = ADAPTER_SPEC_VERSION

    def run(self, request: CameraInjectionRequest) -> CameraInjectionResult:
        raw = inspect_camera_injection(
            frames=request.frames,
            fps=request.fps,
            frame_count=request.frame_count,
            duration_ms=request.duration_ms,
            active_liveness=asdict(request.active_liveness) if request.active_liveness else {},
            replay=asdict(request.replay) if request.replay else {},
            suspicious_threshold=request.suspicious_threshold,
        )
        return CameraInjectionResult(
            status=raw["status"],
            engine=raw["engine"],
            score=raw["score"],
            threshold=raw["threshold"],
            suspicious=raw["suspicious"],
            metadata_score=raw["metadata_score"],
            challenge_timing_score=raw["challenge_timing_score"],
            duplication_score=raw["duplication_score"],
            reason_codes=raw["reason_codes"],
            warnings=raw["warnings"],
            sampled_frame_count=raw["sampled_frame_count"],
        )


def build_capability_registry(settings: Settings) -> CapabilityRegistry:
    """Composition root: the only place that constructs concrete providers.

    Provider construction is lazy (deferred to CapabilityRegistry's internal
    cache on first `.run()`/`.resolve()`), so building this object is cheap
    even before any model artifact is verified - matching today's behavior
    where a missing/invalid manifest never triggers a real model load.
    """
    manifest = ManifestReader(settings.model_dir, settings.model_profile)

    # document_ocr and document_layout share OCR engines (layout does
    # per-region recognition through whichever one layout_ocr_engine() picks,
    # itself built on the same shared LocalOcr detector VietOcr uses); face_embedding
    # is shared between the face_embedding and face_matching registrations.
    # Every other engine below now has exactly one consumer, since face detection/
    # embedding and liveness/deepfake were split into independent
    # single-model classes - no more sharing needed for those.
    _engines: dict[str, Any] = {}

    def shared_ocr() -> LocalOcr:
        if "ocr" not in _engines:
            _engines["ocr"] = LocalOcr(settings.model_dir)
        return _engines["ocr"]

    def shared_vietocr() -> VietOcr:
        if "vietocr" not in _engines:
            _engines["vietocr"] = VietOcr(settings.model_dir, shared_ocr())
        return _engines["vietocr"]

    def layout_ocr_engine() -> LocalOcr | VietOcr:
        """document_layout's field-crop OCR should track document_ocr's own
        primary/fallback semantics (manifest: vietocr-vgg-transformer is "the
        real document_ocr primary across app/benchmark/fieldcheck", rapidocr
        the configured secondary) - plain RapidOCR drops Vietnamese
        diacritics VietOCR gets right (e.g. "Ngo Quyen" -> "Ngo Quyn" on a
        cropped field). Falls back to RapidOCR if vietocr's weights aren't
        available in this profile/scope, same as document_ocr's own chain."""
        try:
            return shared_vietocr()
        except FileNotFoundError:
            return shared_ocr()

    def embedding_provider() -> ArcFaceEmbeddingProvider:
        if "embedding_provider" not in _engines:
            _engines["embedding_provider"] = ArcFaceEmbeddingProvider(
                ArcFaceEmbedder(settings.model_dir)
            )
        return _engines["embedding_provider"]

    registrations: dict[str, ProviderRegistration] = {
        "rapidocr-ppocrv6-small": ProviderRegistration(
            provider_id="rapidocr-ppocrv6-small",
            capability="document_ocr",
            factory=lambda: RapidOcrDocumentProvider(shared_ocr()),
            model_id="rapidocr-ppocrv6-small",
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        ),
        "vietocr-vgg-transformer": ProviderRegistration(
            provider_id="vietocr-vgg-transformer",
            capability="document_ocr",
            factory=lambda: VietOcrDocumentProvider(shared_vietocr()),
            model_id="vietocr-vgg-transformer",
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        ),
        "cccd-layout-yolov11": ProviderRegistration(
            provider_id="cccd-layout-yolov11",
            capability="document_layout",
            factory=lambda: YoloCccdLayoutProvider(
                CccdLayoutOcr(settings.model_dir), layout_ocr_engine()
            ),
            model_id="cccd-layout-yolov11",
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        ),
        "icao-td3-rules": ProviderRegistration(
            provider_id="icao-td3-rules",
            capability="passport_mrz",
            factory=IcaoTd3MrzProvider,
            model_id=None,
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        ),
        "insightface-buffalo-l-scrfd": ProviderRegistration(
            provider_id="insightface-buffalo-l-scrfd",
            capability="face_detection",
            factory=lambda: ScrfdFaceDetectionProvider(ScrfdFaceDetector(settings.model_dir)),
            model_id="insightface-buffalo-l",
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        ),
        "insightface-buffalo-l-arcface": ProviderRegistration(
            provider_id="insightface-buffalo-l-arcface",
            capability="face_embedding",
            factory=embedding_provider,
            model_id="insightface-buffalo-l",
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        ),
        "insightface-buffalo-l-median": ProviderRegistration(
            provider_id="insightface-buffalo-l-median",
            capability="face_matching",
            factory=lambda: MedianFaceMatchingProvider(embedding_provider()),
            model_id="insightface-buffalo-l",
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        ),
        "heuristic-face-quality-v1": ProviderRegistration(
            provider_id="heuristic-face-quality-v1",
            capability="face_quality",
            factory=HeuristicFaceQualityProvider,
            model_id=None,
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        ),
        "minifasnet-v2": ProviderRegistration(
            provider_id="minifasnet-v2",
            capability="passive_liveness",
            factory=lambda: MiniFasNetLivenessProvider(MiniFasNetEngine(settings.model_dir)),
            model_id="minifasnet-v2",
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        ),
        "scrfd-head-pose-rules": ProviderRegistration(
            provider_id="scrfd-head-pose-rules",
            capability="active_liveness",
            factory=HeadPoseActiveLivenessProvider,
            model_id=None,
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        ),
        "deepfake-detector-v2-q4": ProviderRegistration(
            provider_id="deepfake-detector-v2-q4",
            capability="visual_deepfake",
            factory=lambda: DeepfakeDetectorProvider(DeepfakeEngine(settings.model_dir)),
            model_id="deepfake-detector-v2-q4",
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        ),
        "vosk-small-vn-0.4": ProviderRegistration(
            provider_id="vosk-small-vn-0.4",
            capability="voice_challenge",
            factory=lambda: VoskVoiceChallengeProvider(
                VoiceVerifier(settings.model_dir, settings.ai_device)
            ),
            model_id="vosk-small-vn-0.4",
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        ),
        "heuristic-document-quality-v1": ProviderRegistration(
            provider_id="heuristic-document-quality-v1",
            capability="document_quality",
            factory=HeuristicDocumentQualityProvider,
            model_id=None,
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        ),
        "heuristic-replay-v1": ProviderRegistration(
            provider_id="heuristic-replay-v1",
            capability="replay_attack",
            factory=HeuristicReplayProvider,
            model_id=None,
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        ),
        "heuristic-camera-injection-v1": ProviderRegistration(
            provider_id="heuristic-camera-injection-v1",
            capability="camera_injection",
            factory=HeuristicCameraInjectionProvider,
            model_id=None,
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        ),
    }

    chains = build_provider_chains(settings)
    lipsync_url = settings.lipsync_url
    if lipsync_url:
        registrations["syncnet-s3fd-http"] = ProviderRegistration(
            provider_id="syncnet-s3fd-http",
            capability="lip_sync",
            factory=lambda: HttpLipSyncProvider(lipsync_url),
            model_id="syncnet-v2",
            adapter_spec_version=ADAPTER_SPEC_VERSION,
            config_version=CAPABILITY_PROVIDER_CONFIG_VERSION,
        )
    # When `lipsync_url` is unset, "lip_sync" stays in `chains` (from
    # CAPABILITY_PROVIDER_CONFIG) but its provider is never registered, so
    # `.run("lip_sync", ...)` reports UNAVAILABLE/PROVIDER_NOT_REGISTERED -
    # equivalent to today's hardcoded SERVICE_NOT_CONFIGURED short-circuit.

    return CapabilityRegistry(
        manifest,
        chains,
        registrations,
        timeout_seconds=settings.capability_provider_timeout_seconds,
        circuit_failure_threshold=settings.capability_circuit_failure_threshold,
        circuit_cooldown_seconds=settings.capability_circuit_cooldown_seconds,
    )
