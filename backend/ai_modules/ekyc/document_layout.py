from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from ai_modules.ekyc.media import decode_image


class CccdLayoutOcr:
    def __init__(self, model_dir: Path) -> None:
        config_dir = model_dir / ".cache/ultralytics"
        config_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("YOLO_CONFIG_DIR", str(config_dir))
        from ultralytics import YOLO

        self._model = YOLO(str(model_dir / "cccd_layout_yolov11.pt"), task="detect")

    def inspect(
        self, payload: bytes, read_regions: Callable[[np.ndarray], tuple[list[str], list[float]]]
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
            }
        coordinates = boxes.xyxy.cpu().numpy()
        classes = boxes.cls.cpu().numpy().astype(int)
        names = prediction.names
        class_counts: dict[str, int] = {}
        ocr_scores: list[float] = []
        line_count = 0
        for coordinate, class_id in zip(coordinates, classes, strict=True):
            label = str(names.get(int(class_id), class_id))
            class_counts[label] = class_counts.get(label, 0) + 1
            x1, y1, x2, y2 = [int(round(value)) for value in coordinate]
            crop = image[max(0, y1) : min(image.shape[0], y2), max(0, x1) : min(image.shape[1], x2)]
            if crop.size == 0:
                continue
            lines, scores = read_regions(crop)
            line_count += len(lines)
            ocr_scores.extend(scores)
        return {
            "status": "OK",
            "engine": "cccd-layout-yolov11+RapidOCR",
            "region_count": len(coordinates),
            "class_counts": class_counts,
            "ocr_line_count": line_count,
            "mean_ocr_confidence": round(float(np.mean(ocr_scores)), 6) if ocr_scores else None,
        }
