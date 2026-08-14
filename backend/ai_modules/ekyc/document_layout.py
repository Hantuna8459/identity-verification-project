from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from ai_modules.ekyc.media import decode_image

# Raw YOLO class -> canonical field key (ported from the reference project's
# layout pipeline, minus its LLM refinement stage - this project doesn't use
# an LLM for OCR/extraction, see AGENTS.md). Classes absent from this map
# (e.g. "sex", "expiry_date") already match their canonical key.
LAYOUT_FIELD_ALIASES: dict[str, str] = {
    "id": "id_number",
    "name": "full_name",
    "birthday": "date_of_birth",
    "gender": "sex",
    "address": "place_of_residence",
    "birthplace": "place_of_origin",
    "expiry": "expiry_date",
    "id_back": "mrz",
}

# Detected but never sent to field OCR: card outline, corner markers, the
# fingerprint/feature icon, and the portrait (handled by face detection, not OCR).
LAYOUT_SKIP_LABELS = frozenset(
    {
        "feature",
        "portrait",
        "top_left",
        "top_right",
        "bottom_left",
        "bottom_right",
        "new_back_cccd",
        "new_front_cccd",
        "old_back_cccd",
        "old_front_cccd",
    }
)

# Corner-marker classes - not OCR fields, but document_quality's corners
# check (ai_modules.ekyc.document_quality) uses these when available instead
# of its own contour-based fallback, same priority order as the reference
# project's _corners_score_yolo_layout: a trained corner detector beats
# guessing a quadrilateral from Canny edges on a real (often close-cropped)
# phone photo.
LAYOUT_CORNER_LABELS = frozenset({"top_left", "top_right", "bottom_left", "bottom_right"})


def normalize_layout_field_label(label: str) -> str:
    key = label.strip().lower()
    return LAYOUT_FIELD_ALIASES.get(key, key)


class CccdLayoutOcr:
    def __init__(self, model_dir: Path) -> None:
        config_dir = model_dir / ".cache/ultralytics"
        config_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("YOLO_CONFIG_DIR", str(config_dir))
        from ultralytics import YOLO

        self._model = YOLO(str(model_dir / "cccd_layout_yolov11.pt"), task="detect")

    def inspect(
        self,
        payload: bytes,
        read_regions: Callable[[np.ndarray], tuple[list[str], list[float]]],
        *,
        region_ocr_engine_name: str = "RapidOCR",
    ) -> dict[str, Any]:
        image = decode_image(payload)
        predictions: Any = self._model.predict(source=image, device="cpu", verbose=False)
        prediction: Any = predictions[0]
        boxes = prediction.boxes
        if boxes is None or len(boxes) == 0:
            return {
                "status": "INCONCLUSIVE",
                "engine": "cccd-layout-yolov11",
                "region_count": 0,
                "class_counts": {},
                "ocr_line_count": 0,
                "fields": {},
                "corners": {},
            }
        coordinates = boxes.xyxy.cpu().numpy()
        confidences = boxes.conf.cpu().numpy()
        classes = boxes.cls.cpu().numpy().astype(int)
        names = prediction.names

        class_counts: dict[str, int] = {}
        # Best (highest-confidence) box per canonical field label - a field
        # can have multiple raw-class detections (e.g. duplicate "id" boxes),
        # and only one crop per field should go to OCR.
        best_boxes: dict[str, tuple[float, np.ndarray]] = {}
        corner_boxes: dict[str, tuple[float, np.ndarray]] = {}
        for coordinate, confidence, class_id in zip(coordinates, confidences, classes, strict=True):
            raw_label = str(names.get(int(class_id), class_id))
            class_counts[raw_label] = class_counts.get(raw_label, 0) + 1
            if raw_label in LAYOUT_CORNER_LABELS:
                current_corner = corner_boxes.get(raw_label)
                if current_corner is None or float(confidence) > current_corner[0]:
                    corner_boxes[raw_label] = (float(confidence), coordinate)
            if raw_label in LAYOUT_SKIP_LABELS:
                continue
            field_label = normalize_layout_field_label(raw_label)
            current = best_boxes.get(field_label)
            if current is None or float(confidence) > current[0]:
                best_boxes[field_label] = (float(confidence), coordinate)

        fields: dict[str, str] = {}
        ocr_scores: list[float] = []
        line_count = 0
        for field_label, (_, coordinate) in sorted(best_boxes.items()):
            x1, y1, x2, y2 = [int(round(value)) for value in coordinate]
            # Small fixed pad, not scaled to box size: some YOLO boxes on this
            # model are cropped a few px tighter than the actual glyphs, which
            # starves RapidOCR's detector (too small a canvas) even though the
            # text itself isn't cut off - see e.g. the "id" field. A larger or
            # field-category-based pad (tried: extra padding for date fields)
            # was rejected - on this layout several fields sit only ~2px apart
            # vertically, so anything beyond a few px bleeds adjacent fields'
            # text into each other.
            pad = 8
            y1p, y2p = max(0, y1 - pad), min(image.shape[0], y2 + pad)
            x1p, x2p = max(0, x1 - pad), min(image.shape[1], x2 + pad)
            crop = image[y1p:y2p, x1p:x2p]
            if crop.size == 0:
                continue
            lines, scores = read_regions(crop)
            line_count += len(lines)
            ocr_scores.extend(scores)
            text = " ".join(line.strip() for line in lines if line.strip())
            if text:
                fields[field_label] = text

        corners = {
            label: [round(float(value), 2) for value in coordinate]
            for label, (_, coordinate) in corner_boxes.items()
        }

        return {
            "status": "OK",
            "engine": f"cccd-layout-yolov11+{region_ocr_engine_name}",
            "region_count": len(coordinates),
            "class_counts": class_counts,
            "ocr_line_count": line_count,
            "mean_ocr_confidence": round(float(np.mean(ocr_scores)), 6) if ocr_scores else None,
            "fields": fields,
            "corners": corners,
        }
