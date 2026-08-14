from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def _contrast_score(gray: np.ndarray) -> float:
    return float(np.std(gray))


_LAYOUT_CORNER_LABELS = ("top_left", "top_right", "bottom_left", "bottom_right")


def _corner_geometry(
    quad: np.ndarray, *, height: int, width: int, border_margin_ratio: float
) -> tuple[bool, float]:
    """Shared touches_border/coverage_ratio math for a (4, 2) point array,
    regardless of whether the points came from YOLO layout corner boxes or
    contour detection. Returns (touches_border, coverage_ratio)."""
    margin = min(height, width) * border_margin_ratio
    xs, ys = quad[:, 0], quad[:, 1]
    touches_border = bool(
        np.any(xs < margin) or np.any(xs > width - margin) or np.any(ys < margin) or np.any(ys > height - margin)
    )
    coverage_ratio = float(cv2.contourArea(quad.astype(np.float32)) / float(height * width))
    return touches_border, coverage_ratio


def _corner_points_from_layout(layout_corners: dict[str, list[float]] | None) -> np.ndarray | None:
    """Centroid of each YOLO corner-marker box, ordered around the polygon
    perimeter (top_left -> top_right -> bottom_right -> bottom_left) - NOT
    _LAYOUT_CORNER_LABELS' order, which is a self-intersecting "bowtie"
    ordering that makes cv2.contourArea silently compute the wrong (near-
    zero) area instead of raising. Only usable when all 4 corners were
    detected; a partial set can't bound a quadrilateral."""
    if layout_corners is None or not all(label in layout_corners for label in _LAYOUT_CORNER_LABELS):
        return None
    points = []
    for label in ("top_left", "top_right", "bottom_right", "bottom_left"):
        x1, y1, x2, y2 = layout_corners[label]
        points.append([(x1 + x2) / 2.0, (y1 + y2) / 2.0])
    return np.array(points, dtype=np.float32)


def _corners_from_contour(image: np.ndarray) -> np.ndarray | None:
    """Contour-based four-corner detection - the fallback for whenever a
    trained corner detector isn't available (document_layout only covers
    CCCD, not passports; and it may itself find fewer than 4 corners on a
    given photo)."""
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    image_area = float(height * width)
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:8]:
        area = cv2.contourArea(contour)
        if area < image_area * 0.25:
            break
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) == 4:
            return approx.reshape(4, 2).astype(np.float32)
    return None


def _corner_metrics(
    image: np.ndarray,
    *,
    layout_corners: dict[str, list[float]] | None,
    border_margin_ratio: float,
) -> tuple[bool, bool, float | None, str]:
    """Prefers YOLO layout corner-marker boxes over contour detection when
    available - same priority order as the reference project's
    _corners_score_yolo_layout falling back to _corners_score: a trained
    corner detector is expected to be far more reliable than guessing a
    quadrilateral from Canny edges on a real, often close-cropped, phone
    photo - the contour-only fallback failed on a low-quality synthetic test
    image with no clean background/document boundary, though that alone
    doesn't prove it's unreliable on genuine captures too, only that a
    trained detector is the safer default when it's available.

    Returns (corners_detected, touches_border, coverage_ratio, source) where
    source is "layout" | "contour" | "none"."""
    height, width = image.shape[:2]
    quad = _corner_points_from_layout(layout_corners)
    source = "layout"
    if quad is None:
        quad = _corners_from_contour(image)
        source = "contour"
    if quad is None:
        return False, False, None, "none"
    touches_border, coverage_ratio = _corner_geometry(
        quad, height=height, width=width, border_margin_ratio=border_margin_ratio
    )
    return True, touches_border, coverage_ratio, source


def _screenshot_score(gray: np.ndarray) -> float:
    """Higher = more like a genuine camera capture; lower = more likely a
    screenshot/scan of a digital copy. Ported as-is from the reference
    project's _screenshot_score - a tuned heuristic (noise residual + edge
    sharpness/density + flat-region ratio), not something with an obvious
    simpler raw-domain form the way blur/brightness/contrast have."""
    if gray.size == 0:
        return 1.0

    height, width = gray.shape[:2]
    scale = min(1.0, 512.0 / max(height, width))
    if scale < 1.0:
        gray = cv2.resize(gray, (int(width * scale), int(height * scale)))

    smoothed = cv2.GaussianBlur(gray, (3, 3), 0)
    residual = float(np.mean(np.abs(gray.astype(np.float32) - smoothed.astype(np.float32)))) / 255.0
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    edges = cv2.Canny(gray, 80, 180)
    edge_ratio = float(np.count_nonzero(edges)) / edges.size
    mean = cv2.blur(gray.astype(np.float32), (9, 9))
    mean_sq = cv2.blur(gray.astype(np.float32) ** 2, (9, 9))
    local_std = np.sqrt(np.maximum(mean_sq - mean**2, 0.0))
    flat_ratio = float(np.count_nonzero(local_std < 2.0)) / local_std.size

    def clip01(value: float) -> float:
        return float(max(0.0, min(1.0, value)))

    low_noise = clip01((0.006 - residual) / 0.006)
    sharp_edges = clip01((lap_var - 650.0) / 1800.0)
    edge_density = clip01((edge_ratio - 0.035) / 0.12)
    flat_digital_regions = clip01((flat_ratio - 0.35) / 0.4)
    suspicion = max(low_noise * max(sharp_edges, edge_density), flat_digital_regions * sharp_edges)
    return clip01(1.0 - suspicion)


def inspect_document_quality(
    image: np.ndarray,
    *,
    layout_corners: dict[str, list[float]] | None = None,
    blur_threshold: float = 80.0,
    glare_ratio_threshold: float = 0.12,
    dark_threshold: float = 55.0,
    bright_threshold: float = 225.0,
    contrast_threshold: float = 40.0,
    corner_coverage_threshold: float = 0.45,
    corner_border_margin_ratio: float = 0.03,
    screenshot_score_threshold: float = 0.55,
) -> dict[str, Any]:
    """Heuristic document-capture quality signal; no pretrained model.

    Meant to run synchronously right after a document photo is captured -
    see M0_CONTRACT_GOVERNANCE_BASELINE.md's `document_quality` row ("quality
    check before layout/OCR"). Thresholds are untuned defaults; calibrate
    against real phone-captured evidence before relying on them. Six checks,
    ported from the reference project's ekyc_document.quality_check
    (blur/brightness/glare were already here; contrast/corners/screenshot
    are new) - kept as this module's own raw-metric-plus-threshold style
    (matching blur_score/glare_ratio/brightness_mean below) rather than the
    reference's normalized composite score, for consistency with how every
    other capability in this pipeline reports evaluation_only signals.

    `layout_corners` is the CCCD YOLO layout detector's corner-marker boxes
    (EkycOrchestrator passes `document_layout`'s result through when it ran
    first - see _run_document_quality) - the corners check prefers those
    over its own contour-based guess when all 4 are available. Always None
    for passports (no layout model) or when layout hasn't run yet.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness_mean = float(np.mean(gray))
    glare_ratio = float(np.mean(gray >= 250))
    contrast_score = _contrast_score(gray)
    corners_detected, touches_border, corner_coverage_ratio, corner_source = _corner_metrics(
        image, layout_corners=layout_corners, border_margin_ratio=corner_border_margin_ratio
    )
    screenshot_score = _screenshot_score(gray)

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
    if contrast_score < contrast_threshold:
        defect_flags.append("low_contrast")
        reason_codes.append("LOW_CONTRAST")
        warnings.append("Độ tương phản thấp, chữ trên giấy tờ có thể khó đọc.")
    if not corners_detected:
        defect_flags.append("corners_not_detected")
        reason_codes.append("CORNERS_NOT_DETECTED")
        warnings.append("Không xác định được đủ 4 góc giấy tờ trong khung hình.")
    elif touches_border:
        defect_flags.append("document_cropped")
        reason_codes.append("DOCUMENT_CROPPED")
        warnings.append("Giấy tờ có thể bị cắt góc hoặc sát mép khung hình.")
    elif corner_coverage_ratio is not None and corner_coverage_ratio < corner_coverage_threshold:
        defect_flags.append("document_too_small")
        reason_codes.append("DOCUMENT_TOO_SMALL")
        warnings.append("Giấy tờ chiếm diện tích nhỏ trong khung hình, hãy chụp gần hơn.")
    if screenshot_score < screenshot_score_threshold:
        defect_flags.append("likely_screenshot")
        reason_codes.append("LIKELY_SCREENSHOT")
        warnings.append("Ảnh có dấu hiệu chụp lại màn hình/bản scan, nên dùng ảnh chụp trực tiếp bằng camera.")

    return {
        "status": "DEFECT_DETECTED" if defect_flags else "OK",
        "engine": "document-quality-heuristics-v1",
        "blur_score": round(blur_score, 6),
        "glare_ratio": round(glare_ratio, 6),
        "brightness_mean": round(brightness_mean, 6),
        "contrast_score": round(contrast_score, 6),
        "corners_detected": corners_detected,
        "corner_coverage_ratio": round(corner_coverage_ratio, 6) if corner_coverage_ratio is not None else None,
        "corner_source": corner_source,
        "screenshot_score": round(screenshot_score, 6),
        "defect_flags": defect_flags,
        "reason_codes": reason_codes,
        "warnings": warnings,
    }
