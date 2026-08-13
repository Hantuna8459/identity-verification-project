from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def inspect_document_quality(
    image: np.ndarray,
    *,
    blur_threshold: float = 80.0,
    glare_ratio_threshold: float = 0.12,
    dark_threshold: float = 55.0,
    bright_threshold: float = 225.0,
) -> dict[str, Any]:
    """Heuristic document-capture quality signal; no pretrained model.

    Meant to run synchronously right after a document photo is captured -
    see M0_CONTRACT_GOVERNANCE_BASELINE.md's `document_quality` row ("quality
    check before layout/OCR"). Thresholds are untuned defaults; calibrate
    against real phone-captured evidence before relying on them.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness_mean = float(np.mean(gray))
    glare_ratio = float(np.mean(gray >= 250))

    defect_flags: list[str] = []
    reason_codes: list[str] = []
    warnings: list[str] = []

    if blur_score < blur_threshold:
        defect_flags.append("too_blurry")
        reason_codes.append("TOO_BLURRY")
        warnings.append("Ảnh bị mờ, hãy giữ camera ổn định và lấy nét lại.")
    if glare_ratio > glare_ratio_threshold:
        defect_flags.append("glare_detected")
        reason_codes.append("GLARE_DETECTED")
        warnings.append("Phát hiện chói/lóa trên giấy tờ, hãy tránh ánh sáng phản chiếu trực tiếp.")
    if brightness_mean < dark_threshold:
        defect_flags.append("too_dark")
        reason_codes.append("TOO_DARK")
        warnings.append("Ảnh quá tối, hãy chụp ở nơi đủ sáng.")
    if brightness_mean > bright_threshold:
        defect_flags.append("too_bright")
        reason_codes.append("TOO_BRIGHT")
        warnings.append("Ảnh quá sáng/cháy sáng, hãy giảm ánh sáng trực tiếp lên giấy tờ.")

    return {
        "status": "DEFECT_DETECTED" if defect_flags else "OK",
        "engine": "document-quality-heuristics-v1",
        "blur_score": round(blur_score, 6),
        "glare_ratio": round(glare_ratio, 6),
        "brightness_mean": round(brightness_mean, 6),
        "defect_flags": defect_flags,
        "reason_codes": reason_codes,
        "warnings": warnings,
    }
