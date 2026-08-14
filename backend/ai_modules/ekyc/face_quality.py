from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from ai_modules.ekyc.active_liveness import estimate_head_yaw
from ai_modules.ekyc.media import crop

# Per-frame + aggregate face-quality checks over the selfie video - ported
# from the reference project's ekyc_document.biometric.assess_face_quality /
# _validate_portrait_frame_sequence, adapted to this project's raw-metric-
# plus-threshold style (matching document_quality.py) rather than the
# reference's normalized composite score.
#
# Not ported: occlusion detection. Confirmed absent from the reference
# project too (no "occlus*" anywhere in its biometric.py) - a real gap in
# both projects, not something cut here for convenience.
#
# Pose: only yaw (existing ai_modules.ekyc.active_liveness.estimate_head_yaw)
# and roll are modeled. The reference computes full yaw/pitch/roll via a
# calibrated PnP-style estimate; from 5-point SCRFD landmarks alone, pitch
# has no comparably reliable geometric signal without real capture data to
# calibrate against - reporting an uncalibrated pitch number would be worse
# than not reporting one. Yaw + roll already cover the two failure modes
# that matter for "frontal frame" (turned away, head tilted).


def estimate_roll(landmarks: np.ndarray) -> float:
    """Eye-line tilt from horizontal, in radians - 0 when level."""
    points = np.asarray(landmarks, dtype=np.float32).reshape(5, 2)
    dx = float(points[1, 0] - points[0, 0])
    dy = float(points[1, 1] - points[0, 1])
    return float(np.arctan2(dy, dx))


def assess_face_frame(
    image: np.ndarray,
    bbox: np.ndarray,
    landmarks: np.ndarray,
    face_count: int,
) -> dict[str, Any]:
    """Raw per-frame metrics for one already-detected face. No thresholds
    applied here - aggregate_face_quality decides what counts as a defect
    across the whole sampled set."""
    height, width = image.shape[:2]
    x1, y1, x2, y2 = [float(value) for value in bbox]
    face_crop = crop(image, bbox, 1.0)
    blur_score = (
        float(cv2.Laplacian(cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
        if face_crop.size > 0
        else 0.0
    )
    coverage_ratio = max(0.0, x2 - x1) * max(0.0, y2 - y1) / float(height * width)
    in_frame = x1 >= 0.0 and y1 >= 0.0 and x2 <= width and y2 <= height
    yaw = estimate_head_yaw(landmarks)
    roll = estimate_roll(landmarks)
    return {
        "blur_score": round(blur_score, 6),
        "coverage_ratio": round(coverage_ratio, 6),
        "in_frame": in_frame,
        "face_count": face_count,
        "yaw": round(yaw, 6),
        "roll": round(roll, 6),
    }


def aggregate_face_quality(
    frame_assessments: list[dict[str, Any]],
    *,
    min_video_face_frames: int = 8,
    blur_threshold: float = 60.0,
    min_coverage: float = 0.08,
    max_coverage: float = 0.65,
    yaw_threshold: float = 0.08,
    roll_threshold: float = 0.35,
    defect_frame_ratio_threshold: float = 1.0 / 3.0,
) -> dict[str, Any]:
    """Aggregate raw per-frame assessments (from assess_face_frame, one per
    sampled selfie-video frame with a detected face) into a single
    evaluation_only signal. `yaw_threshold` reuses the exact "centered"
    definition ai_modules.ekyc.active_liveness.inspect_head_turn_sequence
    already uses for its own center_threshold, rather than inventing a
    second, inconsistent notion of "frontal" in this same pipeline."""
    sample_count = len(frame_assessments)
    defect_flags: list[str] = []
    reason_codes: list[str] = []
    warnings: list[str] = []

    if sample_count < min_video_face_frames:
        defect_flags.append("insufficient_face_frames")
        reason_codes.append("INSUFFICIENT_FACE_FRAMES")
        warnings.append(
            f"Chỉ có {sample_count} frame nhận diện được khuôn mặt, cần tối thiểu "
            f"{min_video_face_frames}. Hãy quay video rõ mặt hơn."
        )

    multi_face_frame_count = sum(1 for item in frame_assessments if item["face_count"] != 1)
    if multi_face_frame_count:
        defect_flags.append("multiple_faces_detected")
        reason_codes.append("MULTIPLE_FACES_DETECTED")
        warnings.append("Phát hiện nhiều hơn một khuôn mặt trong video.")

    def _flag_if_common(predicate, flag: str, reason: str, warning: str) -> None:
        count = sum(1 for item in frame_assessments if predicate(item))
        if sample_count and count > max(1, sample_count * defect_frame_ratio_threshold):
            defect_flags.append(flag)
            reason_codes.append(reason)
            warnings.append(warning)

    _flag_if_common(
        lambda item: item["coverage_ratio"] < min_coverage,
        "face_too_small",
        "FACE_TOO_SMALL",
        "Khuôn mặt quá nhỏ trong phần lớn video, hãy đưa camera lại gần hơn.",
    )
    _flag_if_common(
        lambda item: item["coverage_ratio"] > max_coverage,
        "face_too_large",
        "FACE_TOO_LARGE",
        "Khuôn mặt quá sát camera trong phần lớn video, hãy lùi camera ra xa hơn.",
    )
    _flag_if_common(
        lambda item: item["blur_score"] < blur_threshold,
        "face_blurry",
        "FACE_BLURRY",
        "Khuôn mặt bị mờ trong phần lớn video, hãy giữ camera ổn định.",
    )
    _flag_if_common(
        lambda item: not item["in_frame"],
        "face_out_of_frame",
        "FACE_OUT_OF_FRAME",
        "Khuôn mặt bị ra khỏi khung hình trong phần lớn video.",
    )

    frontal_frame_found = any(
        abs(item["yaw"]) <= yaw_threshold and abs(item["roll"]) <= roll_threshold
        for item in frame_assessments
    )
    if frame_assessments and not frontal_frame_found:
        defect_flags.append("no_frontal_frame")
        reason_codes.append("NO_FRONTAL_FRAME_FOUND")
        warnings.append("Không tìm thấy khung hình nào có khuôn mặt nhìn thẳng, rõ nét.")

    return {
        "status": "DEFECT_DETECTED" if defect_flags else "OK",
        "engine": "face-quality-heuristics-v1",
        "sampled_frame_count": sample_count,
        "multi_face_frame_count": multi_face_frame_count,
        "frontal_frame_found": frontal_frame_found,
        "defect_flags": defect_flags,
        "reason_codes": reason_codes,
        "warnings": warnings,
    }
