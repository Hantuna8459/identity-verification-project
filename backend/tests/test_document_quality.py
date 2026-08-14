from __future__ import annotations

import cv2
import numpy as np

from ai_modules.ekyc.document_quality import inspect_document_quality
from app.adapters.ekyc_providers import HeuristicDocumentQualityProvider
from app.domain.capability_ports import DocumentQualityRequest, DocumentQualityResult


def _document_photo(*, right_margin: int = 30, tone_gap: int = 140, seed: int = 0) -> np.ndarray:
    """A synthetic "document photo": a lighter rectangle (with a few dark
    text-like lines for edge/Laplacian variance) against a darker background,
    plus mild per-pixel camera-grain noise. Needs an actual rectangle-vs-
    background edge (not texture filling the whole frame) for the corners
    check to find a quadrilateral, and needs the grain - flat geometric
    shapes with no noise read as "digital" to the screenshot heuristic.
    `right_margin` below the ~9px border-touch margin (300 * 0.03) still
    leaves a traceable rectangle but flags it as touching the border."""
    size, margin, base = 300, 30, 60
    frame = np.full((size, size), base, dtype=np.float32)
    right = size - right_margin
    cv2.rectangle(frame, (margin, margin), (right, size - margin), base + tone_gap, thickness=-1)
    for i in range(10):
        y = margin + 20 + i * 20
        cv2.line(frame, (margin + 15, y), (right - 15, y), base - 20, thickness=3)
    noise = np.random.default_rng(seed).normal(0, 8, size=frame.shape).astype(np.float32)
    frame = np.clip(frame + noise, 0, 255).astype(np.uint8)
    return np.repeat(frame[:, :, None], 3, axis=2)


def _textured_gray_image() -> np.ndarray:
    return _document_photo()


def test_inspect_document_quality_ok_for_sharp_moderate_image() -> None:
    result = inspect_document_quality(_textured_gray_image())

    assert result["status"] == "OK"
    assert result["defect_flags"] == []
    assert result["blur_score"] > 80.0
    assert result["glare_ratio"] == 0.0


def test_inspect_document_quality_flags_blur_on_flat_image() -> None:
    flat = np.full((200, 200, 3), 128, dtype=np.uint8)

    result = inspect_document_quality(flat)

    assert result["status"] == "DEFECT_DETECTED"
    assert "too_blurry" in result["defect_flags"]
    assert "TOO_BLURRY" in result["reason_codes"]


def test_inspect_document_quality_flags_too_dark() -> None:
    dark = np.full((200, 200, 3), 20, dtype=np.uint8)

    result = inspect_document_quality(dark)

    assert "too_dark" in result["defect_flags"]


def test_inspect_document_quality_flags_glare() -> None:
    image = np.full((200, 200, 3), 130, dtype=np.uint8)
    image[:100, :100] = 255  # 25% of the frame near-white - above the 12% threshold

    result = inspect_document_quality(image)

    assert "glare_detected" in result["defect_flags"]
    assert result["glare_ratio"] > 0.12


def test_inspect_document_quality_flags_corners_not_detected_on_flat_image() -> None:
    flat = np.full((200, 200, 3), 128, dtype=np.uint8)

    result = inspect_document_quality(flat)

    assert result["corners_detected"] is False
    assert "corners_not_detected" in result["defect_flags"]
    assert "CORNERS_NOT_DETECTED" in result["reason_codes"]


def test_inspect_document_quality_flags_document_cropped_when_touching_border() -> None:
    # right_margin=5 is below the ~9px border-touch margin (300 * 0.03).
    result = inspect_document_quality(_document_photo(right_margin=5))

    assert result["corners_detected"] is True
    assert "document_cropped" in result["defect_flags"]
    assert "DOCUMENT_CROPPED" in result["reason_codes"]


def test_inspect_document_quality_flags_low_contrast() -> None:
    result = inspect_document_quality(_document_photo(tone_gap=15))

    assert result["contrast_score"] < 40.0
    assert "low_contrast" in result["defect_flags"]
    assert "LOW_CONTRAST" in result["reason_codes"]


def test_inspect_document_quality_prefers_layout_corners_over_contour() -> None:
    # Real box coordinates from a YOLO layout run that once computed a
    # near-zero coverage_ratio due to a self-intersecting point ordering -
    # regression coverage for that bug (see _corner_points_from_layout).
    layout_corners = {
        "top_left": [373.66, 121.79, 398.41, 151.78],
        "top_right": [1037.13, 121.23, 1061.9, 147.69],
        "bottom_left": [354.41, 532.12, 379.34, 558.33],
        "bottom_right": [1049.93, 530.35, 1073.47, 558.76],
    }
    image = np.full((700, 1400, 3), 100, dtype=np.uint8)

    result = inspect_document_quality(image, layout_corners=layout_corners)

    assert result["corners_detected"] is True
    assert result["corner_source"] == "layout"
    # The quad spans most of the 1400x700 frame - coverage should reflect
    # that, not the ~0.006 a self-intersecting polygon area would give.
    assert result["corner_coverage_ratio"] > 0.2


def test_inspect_document_quality_falls_back_to_contour_when_layout_corners_incomplete() -> None:
    result = inspect_document_quality(
        _textured_gray_image(), layout_corners={"top_left": [10.0, 10.0, 20.0, 20.0]}
    )

    assert result["corner_source"] == "contour"


def test_heuristic_document_quality_provider_wraps_result() -> None:
    provider = HeuristicDocumentQualityProvider()

    result = provider.run(DocumentQualityRequest(image=_textured_gray_image()))

    assert isinstance(result, DocumentQualityResult)
    assert result.status == "OK"
    assert result.engine == "document-quality-heuristics-v1"
    assert result.defect_flags == []
