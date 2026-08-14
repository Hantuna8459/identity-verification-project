from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.local", "../env/.env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        enable_decoding=False,
    )

    project_name: str = "V-ID eKYC"
    environment: str = "development"
    api_prefix: str = "/api/v2"
    database_url: str = f"sqlite:///{DEFAULT_DATA_DIR / 'vid_ekyc.db'}"
    frontend_url: str = "http://localhost:3000"
    cors_origins: list[str] = ["http://localhost:3000"]
    token_secret: str = "change-this-token-secret"
    evidence_key: str = "change-this-evidence-key"
    evidence_dir: Path = DEFAULT_DATA_DIR / "evidence"
    vid_client_key: str = "local-vid-client-key"
    reviewer_token: str = "local-reviewer-token"
    session_ttl_minutes: int = 30
    handoff_ttl_seconds: int = 300
    capture_ttl_minutes: int = 30
    purge_interval_hours: int = 24
    development_retention_hours: int = 168
    max_document_size_mb: int = 10
    max_video_size_mb: int = 50
    webhook_allowlist: list[str] = []
    model_dir: Path = Path("../models")
    require_models: bool = False
    model_profile: str = "technical_demo"
    ai_device: str = "cpu"
    lipsync_url: str | None = None
    max_video_frames: int = 36
    max_face_match_frames: int = 12
    replay_suspicious_threshold: float = 0.62
    camera_injection_suspicious_threshold: float = 0.60
    # Copied from the reference project (C2-App-036/.env.example), which
    # defaults to the same InsightFace buffalo_l embedding and the same HF
    # ViT deepfake-detector family this project uses - not a blind
    # cross-model guess. Evaluation-only per docs/M0_CONTRACT_GOVERNANCE_
    # BASELINE.md and AGENTS.md's open decisions list (production
    # auto-approve/reject policy is not yet decided) - see analyzer.py's
    # approval_status: "EVALUATION_ONLY" on these three capabilities.
    face_match_threshold: float = 0.45
    face_match_consider_threshold: float = 0.30
    passive_liveness_threshold: float = 0.65
    passive_liveness_consider_threshold: float = 0.45
    visual_deepfake_threshold: float = 0.68
    # min/max_coverage and min_video_face_frames copied from C2-App-036's
    # EKYC_MIN_FACE_COVERAGE/EKYC_MAX_FACE_COVERAGE/EKYC_MIN_VIDEO_FACE_FRAMES.
    # blur/yaw/roll thresholds are this project's own - blur has no reference
    # equivalent to copy (its assess_face_quality scores blur on a 0-1 scale
    # this project doesn't use, see ai_modules.ekyc.face_quality); yaw reuses
    # active_liveness's own already-tuned center_threshold (0.08) rather than
    # inventing a second "frontal" definition; roll is new, untuned.
    face_quality_min_video_face_frames: int = 8
    face_quality_blur_threshold: float = 60.0
    face_quality_min_coverage: float = 0.08
    face_quality_max_coverage: float = 0.65
    face_quality_yaw_threshold: float = 0.08
    face_quality_roll_threshold: float = 0.35
    demo_ocr_rerun_enabled: bool = False
    capability_provider_timeout_seconds: float = 30.0
    capability_circuit_failure_threshold: int = 3
    capability_circuit_cooldown_seconds: float = 60.0

    # Capability -> "primary[,secondary]" provider id. Environment config, not
    # a business decision to hard-code: which vendor/model is live in a given
    # deployment is operational information and should not sit fixed in git
    # history. These defaults are the technical-demo baseline only; a
    # pilot/production deployment overrides them via its own `.env`.
    provider_document_ocr: str = "vietocr-vgg-transformer,rapidocr-ppocrv6-small"
    provider_document_layout: str = "cccd-layout-yolov11"
    provider_document_quality: str = "heuristic-document-quality-v1"
    provider_face_quality: str = "heuristic-face-quality-v1"
    provider_passport_mrz: str = "icao-td3-rules"
    provider_face_detection: str = "insightface-buffalo-l-scrfd"
    provider_face_embedding: str = "insightface-buffalo-l-arcface"
    provider_face_matching: str = "insightface-buffalo-l-median"
    provider_passive_liveness: str = "minifasnet-v2"
    provider_active_liveness: str = "scrfd-head-pose-rules"
    provider_visual_deepfake: str = "deepfake-detector-v2-q4"
    provider_voice_challenge: str = "vosk-small-vn-0.4"
    provider_lip_sync: str = "syncnet-s3fd-http"
    provider_replay_attack: str = "heuristic-replay-v1"
    provider_camera_injection: str = "heuristic-camera-injection-v1"

    @field_validator("cors_origins", "webhook_allowlist", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
