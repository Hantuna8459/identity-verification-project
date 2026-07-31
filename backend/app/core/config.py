from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        enable_decoding=False,
    )

    project_name: str = "V-ID eKYC"
    environment: str = "development"
    api_prefix: str = "/api/v2"
    database_url: str = "sqlite:///./data/vid_ekyc.db"
    frontend_url: str = "http://localhost:3000"
    cors_origins: list[str] = ["http://localhost:3000"]
    token_secret: str = "change-this-token-secret"
    evidence_key: str = "change-this-evidence-key"
    evidence_dir: Path = Path("./data/evidence")
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
    replay_suspicious_threshold: float = 0.62
    camera_injection_suspicious_threshold: float = 0.60
    demo_ocr_rerun_enabled: bool = False

    @field_validator("cors_origins", "webhook_allowlist", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
