from __future__ import annotations

import numpy as np

from ai_modules.ekyc.document_quality import inspect_document_quality
from app.adapters.ekyc_providers import HeuristicDocumentQualityProvider
from app.domain.capability_ports import DocumentQualityRequest, DocumentQualityResult


def _textured_gray_image() -> np.ndarray:
    """Plenty of local edge/texture (high Laplacian variance), moderate
    brightness, no near-white pixels - the clean "no defects" case."""
    rng = np.random.default_rng(0)
    raw = rng.integers(0, 256, size=(200, 200), endpoint=False)
    gray = (90 + raw / 255.0 * 110).astype(np.uint8)
    return np.repeat(gray[:, :, None], 3, axis=2)


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


def test_heuristic_document_quality_provider_wraps_result() -> None:
    provider = HeuristicDocumentQualityProvider()

    result = provider.run(DocumentQualityRequest(image=_textured_gray_image()))

    assert isinstance(result, DocumentQualityResult)
    assert result.status == "OK"
    assert result.engine == "document-quality-heuristics-v1"
    assert result.defect_flags == []
