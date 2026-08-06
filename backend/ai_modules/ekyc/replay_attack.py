from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def _gray_frame(frame: np.ndarray, size: tuple[int, int] = (32, 32)) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    return cv2.resize(gray, size, interpolation=cv2.INTER_AREA).astype(np.float32)


def _binary_hash(frame: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    return resized[:, 1:] > resized[:, :-1]


def _duplicate_stats(frames: list[np.ndarray]) -> tuple[float, int]:
    if len(frames) < 2:
        return 0.0, 0
    hashes = [_binary_hash(frame) for frame in frames]
    duplicate_pairs = sum(
        int(np.count_nonzero(left != right) <= 2)
        for left, right in zip(hashes, hashes[1:], strict=False)
    )
    comparisons = len(hashes) - 1
    return float(np.clip(duplicate_pairs / max(comparisons, 1) / 0.55, 0.0, 1.0)), duplicate_pairs


def _motion_score(frames: list[np.ndarray]) -> float:
    if len(frames) < 2:
        return 0.0
    differences = []
    previous = _gray_frame(frames[0])
    for frame in frames[1:]:
        current = _gray_frame(frame)
        differences.append(float(np.mean(np.abs(current - previous)) / 255.0))
        previous = current
    return float(np.clip(np.mean(differences) * 8.0, 0.0, 1.0))


def _flicker_score(frames: list[np.ndarray]) -> float:
    if len(frames) < 2:
        return 0.0
    means = [float(np.mean(_gray_frame(frame))) for frame in frames]
    jumps = np.abs(np.diff(np.asarray(means, dtype=np.float32))) / 255.0
    return float(np.clip(np.mean(jumps) * 8.0, 0.0, 1.0))


def _moire_score(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (128, 128), interpolation=cv2.INTER_AREA).astype(np.float32)
    small -= float(np.mean(small))
    spectrum = np.abs(np.fft.fftshift(np.fft.fft2(small)))
    height, width = spectrum.shape
    center_y, center_x = height / 2, width / 2
    yy, xx = np.ogrid[:height, :width]
    radius = np.sqrt((yy - center_y) ** 2 + (xx - center_x) ** 2)
    total = float(np.sum(spectrum)) + 1e-6
    low_band = float(np.sum(spectrum[radius <= 20]) / total)
    mid_band = float(np.sum(spectrum[(radius > 28) & (radius <= 48)]) / total)
    high_ratio = float(np.sum(spectrum[radius > 34]) / total)
    periodic = float(np.clip(max(0.0, mid_band / max(low_band, 1e-6) - 1.15) / 2.2, 0.0, 1.0))
    row_energy = float(np.mean(np.abs(np.diff(small, axis=0))))
    col_energy = float(np.mean(np.abs(np.diff(small, axis=1))))
    grid = float(
        np.clip(abs(row_energy - col_energy) / max(row_energy + col_energy, 1e-6) * 3.0, 0.0, 1.0)
    )
    compression = float(np.clip(max(0.0, high_ratio - 0.22) / 0.35, 0.0, 1.0))
    return float(np.clip(periodic * 0.55 + grid * 0.25 + compression * 0.20, 0.0, 1.0))


def inspect_replay_attack(
    frames: list[np.ndarray],
    *,
    suspicious_threshold: float = 0.62,
) -> dict[str, Any]:
    """Heuristic replay signal; no pretrained model or raw frames are returned."""
    if len(frames) < 2:
        return {
            "status": "INCONCLUSIVE",
            "engine": "replay-camera-heuristics-v1",
            "score": 0.0,
            "threshold": suspicious_threshold,
            "confirmed": False,
            "duplicate_pairs": 0,
            "reason": "INSUFFICIENT_FRAMES",
            "warnings": ["Không đủ frame để kiểm tra replay attack."],
        }
    duplication_score, duplicate_pairs = _duplicate_stats(frames)
    motion_score = _motion_score(frames)
    flicker_score = _flicker_score(frames)
    moire_score = float(np.mean([_moire_score(frame) for frame in frames]))
    if motion_score >= 0.28:
        duplication_score *= 0.45
    raw_score = float(
        np.clip(moire_score * 0.22 + flicker_score * 0.13 + duplication_score * 0.65, 0.0, 1.0)
    )
    confirmed = bool(
        duplication_score >= 0.52 and (flicker_score >= 0.68 or duplication_score >= 0.82)
    )
    score = raw_score if confirmed else raw_score * 0.35
    warnings: list[str] = []
    reasons: list[str] = []
    if moire_score >= 0.68:
        reasons.append("MOIRE_OR_FLICKER")
        warnings.append("Phát hiện pattern nhấp nháy/moire bất thường giữa các frame.")
    if duplication_score >= 0.52:
        reasons.append("DUPLICATED_FRAMES")
        warnings.append("Nhiều frame gần như trùng lặp, nghi replay hoặc stream bị inject.")
    suspicious = confirmed and score >= suspicious_threshold
    return {
        "status": "OK",
        "engine": "replay-camera-heuristics-v1",
        "score": round(score, 6),
        "threshold": suspicious_threshold,
        "suspicious": suspicious,
        "confirmed": confirmed,
        "moire_score": round(moire_score, 6),
        "flicker_score": round(flicker_score, 6),
        "duplication_score": round(duplication_score, 6),
        "duplicate_pairs": duplicate_pairs,
        "face_motion_score": round(motion_score, 6),
        "reason_codes": reasons,
        "warnings": warnings,
    }
