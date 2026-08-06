from __future__ import annotations

import numpy as np

from ai_modules.ekyc.errors import InvalidEvidenceError
from app.domain.capability_ports import FaceDetectionResult

# Pure math over the normalized FaceDetectionResult contract (not a raw model
# dict) - lives in domain, not ai_modules, precisely because it depends on
# that contract rather than any one engine's output shape.


def select_face_match_candidates(
    candidates: list[tuple[np.ndarray, FaceDetectionResult]], maximum: int
) -> list[tuple[np.ndarray, FaceDetectionResult]]:
    """Keep the strongest detected faces while bounding embedding inference cost."""
    return sorted(candidates, key=lambda item: item[1].score, reverse=True)[: max(1, maximum)]


def aggregate_face_similarities(similarities: list[float]) -> float:
    """Use a robust multi-frame score instead of an optimistic best-frame score."""
    if not similarities:
        raise InvalidEvidenceError("No selfie face could be embedded")
    return float(np.median(np.asarray(similarities, dtype=np.float32)))
