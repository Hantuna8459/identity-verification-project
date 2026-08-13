from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Protocol, TypeVar

import numpy as np

CapabilityName = Literal[
    "document_ocr",
    "document_layout",
    "passport_mrz",
    "face_detection",
    "face_embedding",
    "face_matching",
    "passive_liveness",
    "active_liveness",
    "visual_deepfake",
    "voice_challenge",
    "lip_sync",
    "replay_attack",
    "camera_injection",
    "document_quality",
    "speech_verification",
]

ProviderRole = Literal["primary", "secondary"]
AttemptStatus = Literal["COMPLETED", "TIMEOUT", "INVALID_OUTPUT", "UNAVAILABLE", "FAILED"]


@dataclass(frozen=True)
class ProviderChain:
    """Capability -> provider selection for one profile; a versioned policy value."""

    primary: str
    secondary: str | None = None


@dataclass(frozen=True)
class Attempt:
    """One provider try for a capability call; see ekyc-analysis/1.0 adapter spec."""

    provider_id: str
    provider_role: ProviderRole
    model_id: str | None
    model_revision: str | None
    manifest_entry_id: str | None
    adapter_spec_version: str
    config_version: str
    started_at: datetime
    duration_ms: int
    status: AttemptStatus
    reason_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_role": self.provider_role,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "manifest_entry_id": self.manifest_entry_id,
            "adapter_spec_version": self.adapter_spec_version,
            "config_version": self.config_version,
            "threshold_profile": "none",
            "threshold_version": None,
            "started_at": self.started_at.isoformat(),
            "duration_ms": self.duration_ms,
            "status": self.status,
            "reason_codes": list(self.reason_codes),
        }


ReqT = TypeVar("ReqT", contravariant=True)
ResT = TypeVar("ResT", covariant=True)


class CapabilityProvider(Protocol[ReqT, ResT]):
    """A single capability/model implementation selectable by composition/config.

    Concrete providers never decide fallback or record attempts themselves -
    that is CapabilityRegistry's job (ADR-M0-001/ADR-M0-002). A provider only
    runs its request and raises on failure; InvalidEvidenceError signals a
    business/input-quality failure (not fallback-eligible), any other
    exception signals a technical failure (fallback-eligible).
    """

    provider_id: str
    model_id: str | None
    adapter_spec_version: str

    def run(self, request: ReqT) -> ResT: ...


# --- Per-capability request/result payloads -------------------------------
# Each provider's `run()` returns a typed *Result dataclass, never a bare
# dict: the provider is the adapter (M0 Section 4) responsible for mapping
# whatever shape its underlying model/engine produces onto this fixed
# contract, so swapping which provider is configured for a capability can't
# silently change field names/types out from under the analyzer. Serialized
# via `dataclasses.asdict()` at the orchestrator boundary (see
# EkycOrchestrator._run) - field names are already the exact keys the
# analysis contract/reviewer surface expects.


@dataclass(frozen=True)
class DocumentOcrRequest:
    payload: bytes


@dataclass(frozen=True)
class DocumentLayoutRequest:
    payload: bytes


@dataclass(frozen=True)
class PassportMrzRequest:
    lines: list[str]


@dataclass(frozen=True)
class FaceDetectionRequest:
    image: np.ndarray


@dataclass(frozen=True)
class FaceEmbeddingRequest:
    image: np.ndarray
    landmarks: np.ndarray


@dataclass(frozen=True)
class FaceMatchingRequest:
    document_image: np.ndarray
    document_face: FaceDetectionResult
    live_candidates: list[tuple[np.ndarray, FaceDetectionResult]]
    max_frames: int
    sampled_frame_count: int


@dataclass(frozen=True)
class PassiveLivenessRequest:
    image: np.ndarray
    bbox: np.ndarray


@dataclass(frozen=True)
class ActiveLivenessRequest:
    yaw_samples: list[float]


@dataclass(frozen=True)
class VisualDeepfakeRequest:
    image: np.ndarray
    bbox: np.ndarray


@dataclass(frozen=True)
class VoiceChallengeRequest:
    media_path: Path
    challenge: str


@dataclass(frozen=True)
class LipSyncRequest:
    media_path: Path
    content_type: str


@dataclass(frozen=True)
class DocumentQualityRequest:
    image: np.ndarray


@dataclass(frozen=True)
class ReplayAttackRequest:
    frames: list[np.ndarray]
    suspicious_threshold: float


@dataclass(frozen=True)
class CameraInjectionRequest:
    frames: list[np.ndarray]
    fps: float | None
    frame_count: int | None
    duration_ms: float | None
    # None when active_liveness/replay_attack themselves failed - the
    # heuristic tolerates missing upstream signal (see HeuristicCameraInjectionProvider).
    active_liveness: ActiveLivenessResult | None
    replay: ReplayAttackResult | None
    suspicious_threshold: float


# --- Per-capability normalized results -------------------------------------


@dataclass(frozen=True)
class FaceDetectionResult:
    score: float
    bbox: np.ndarray
    landmarks: np.ndarray


@dataclass(frozen=True)
class DocumentOcrResult:
    status: str
    engine: str
    line_count: int
    mean_confidence: float | None
    lines: list[str]


@dataclass(frozen=True)
class DocumentLayoutResult:
    status: str
    engine: str
    region_count: int
    class_counts: dict[str, int]
    ocr_line_count: int
    mean_ocr_confidence: float | None = None


@dataclass(frozen=True)
class PassportMrzResult:
    status: str
    format: str
    mrz_detected: bool
    all_check_digits_valid: bool
    line_lengths: list[int] | None = None
    check_digits: dict[str, bool] | None = None


@dataclass(frozen=True)
class FaceMatchingResult:
    status: str
    engine: str
    cosine_similarity: float
    sampled_frames: int
    frames_with_face: int
    matched_frames: int
    aggregation: str


@dataclass(frozen=True)
class PassiveLivenessResult:
    status: str
    engine: str
    live_probability: float


@dataclass(frozen=True)
class ActiveLivenessResult:
    status: str
    engine: str
    sequence_complete: bool
    completed_step_count: int
    required_step_count: int
    sampled_pose_count: int
    reason: str | None = None


@dataclass(frozen=True)
class VisualDeepfakeResult:
    status: str
    engine: str
    manipulation_probability: float


@dataclass(frozen=True)
class VoiceChallengeResult:
    status: str
    engine: str
    challenge_length: int
    recognized_digit_count: int
    similarity: float


@dataclass(frozen=True)
class LipSyncResult:
    status: str
    engine: str
    verdict: str | None
    confidence: float | None
    manipulation_probability: float | None


@dataclass(frozen=True)
class DocumentQualityResult:
    status: str
    engine: str
    blur_score: float
    glare_ratio: float
    brightness_mean: float
    defect_flags: list[str]
    reason_codes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReplayAttackResult:
    status: str
    engine: str
    score: float
    threshold: float
    confirmed: bool
    duplicate_pairs: int
    warnings: list[str]
    suspicious: bool = False
    moire_score: float | None = None
    flicker_score: float | None = None
    duplication_score: float | None = None
    face_motion_score: float | None = None
    reason_codes: list[str] = field(default_factory=list)
    reason: str | None = None


@dataclass(frozen=True)
class CameraInjectionResult:
    status: str
    engine: str
    score: float
    threshold: float
    suspicious: bool
    metadata_score: float
    challenge_timing_score: float
    duplication_score: float
    reason_codes: list[str]
    warnings: list[str]
    sampled_frame_count: int
