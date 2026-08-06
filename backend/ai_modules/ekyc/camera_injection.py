from __future__ import annotations

from typing import Any

import numpy as np


def inspect_camera_injection(
    *,
    frames: list[np.ndarray],
    fps: float | None,
    frame_count: int | None,
    duration_ms: float | None,
    active_liveness: dict[str, Any],
    replay: dict[str, Any],
    suspicious_threshold: float = 0.65,
) -> dict[str, Any]:
    """Combine container/timing/duplication signals for camera injection review."""
    metadata_flags = sum(
        [
            not fps or fps <= 0.0,
            not frame_count or frame_count <= 0,
            duration_ms is None or duration_ms < 800.0,
        ]
    )
    metadata_score = metadata_flags / 3.0
    sequence_complete = active_liveness.get("sequence_complete") is True
    sampled_pose_count = int(active_liveness.get("sampled_pose_count", 0) or 0)
    challenge_timing_score = (
        (0.55 if not sequence_complete else 0.0)
        + (0.35 if duration_ms is not None and duration_ms < 1200.0 else 0.0)
        + (0.25 if sampled_pose_count < 5 else 0.0)
    )
    challenge_timing_score = float(np.clip(challenge_timing_score, 0.0, 1.0))
    duplication_score = float(replay.get("duplication_score", 0.0) or 0.0)
    score = float(
        np.clip(
            metadata_score * 0.30 + challenge_timing_score * 0.35 + duplication_score * 0.35,
            0.0,
            1.0,
        )
    )
    reason_codes: list[str] = []
    warnings: list[str] = []
    if metadata_score >= 0.5:
        reason_codes.append("VIDEO_METADATA_ANOMALY")
        warnings.append("Metadata video thiếu hoặc bất thường.")
    if challenge_timing_score >= 0.6:
        reason_codes.append("CHALLENGE_TIMING_ANOMALY")
        warnings.append("Timing/phản hồi challenge không nhất quán với camera live.")
    if duplication_score >= 0.6:
        reason_codes.append("FRAME_DUPLICATION")
        warnings.append("Frame duplication làm tăng rủi ro camera injection.")
    suspicious = bool(
        score >= suspicious_threshold and (bool(replay.get("confirmed")) or metadata_score >= 0.67)
    )
    return {
        "status": "OK",
        "engine": "replay-camera-heuristics-v1",
        "score": round(score, 6),
        "threshold": suspicious_threshold,
        "suspicious": suspicious,
        "metadata_score": round(metadata_score, 6),
        "challenge_timing_score": round(challenge_timing_score, 6),
        "duplication_score": round(duplication_score, 6),
        "reason_codes": reason_codes,
        "warnings": warnings,
        "sampled_frame_count": len(frames),
    }
