from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from rapidocr import RapidOCR

from ai_modules.ekyc.media import decode_image


class LocalOcr:
    def __init__(self, model_dir: Path) -> None:
        root = model_dir / "rapidocr"
        params = {
            "Global.model_root_dir": str(root),
            "Det.model_path": str(root / "PP-OCRv6_det_small.onnx"),
            "Rec.model_path": str(root / "PP-OCRv6_rec_small.onnx"),
            "Cls.model_path": str(root / "ch_ppocr_mobile_v2.0_cls_mobile.onnx"),
        }
        self._engine = RapidOCR(config_path=str(root / "config.yaml"), params=params)

    def detect_boxes(self, image: np.ndarray) -> np.ndarray:
        """Text-line boxes only, no recognition - reused by `VietOcr` as its
        detector, since vietocr itself is a line-level recognizer with no
        detection stage of its own (see `VietOcr` below)."""
        output: Any = self._engine(image, use_det=True, use_cls=False, use_rec=False)
        boxes = output.boxes
        return boxes if boxes is not None else np.empty((0, 4, 2))

    def read_array(self, image: np.ndarray) -> tuple[list[str], list[float]]:
        # Explicit flags, not defaults: RapidOCR.update_params() ignores None
        # and otherwise keeps whatever use_det/use_cls/use_rec the engine was
        # last called with - detect_boxes() below leaves it in det-only mode,
        # which would silently starve this call of recognition output.
        output: Any = self._engine(image, use_det=True, use_cls=True, use_rec=True)
        return list(output.txts or ()), [float(score) for score in (output.scores or ())]

    def read(self, payload: bytes) -> tuple[list[str], list[float]]:
        return self.read_array(decode_image(payload))

    def inspect_document(self, payload: bytes) -> dict[str, Any]:
        lines, scores = self.read(payload)
        return {
            "status": "OK" if lines else "INCONCLUSIVE",
            "engine": "rapidocr-3.9.2/PP-OCRv6-small",
            "line_count": len(lines),
            "mean_confidence": round(float(np.mean(scores)), 6) if scores else None,
            "lines": lines,
        }


def _crop_box(image: np.ndarray, box: np.ndarray) -> np.ndarray:
    x1 = max(0, int(np.floor(box[:, 0].min())))
    y1 = max(0, int(np.floor(box[:, 1].min())))
    x2 = min(image.shape[1], int(np.ceil(box[:, 0].max())))
    y2 = min(image.shape[0], int(np.ceil(box[:, 1].max())))
    return image[y1:y2, x1:x2]


class VietOcr:
    """VGG-Transformer recognizer paired with `LocalOcr`'s detector.

    vietocr recognizes only an already-cropped single line, with no
    detection stage of its own (see `benchmark/engines/vietocr_engine.py`).
    Full-page OCR therefore needs a detector in front of it; `LocalOcr`'s
    RapidOCR Det model - already a required artifact for the rapidocr
    provider - fills that role instead of shipping a second detector.

    Always loads config/weights from local files, never vocr.vn: vietocr's
    own `Cfg.load_config_from_name()`/`Predictor()` reach the network by
    default, which the M0 governance rule "adapter không được tự download
    model hoặc artifact runtime" forbids.
    """

    def __init__(self, model_dir: Path, detector: LocalOcr) -> None:
        root = model_dir / "vietocr"
        weights_path = root / "vietocr_vgg_transformer.pth"
        config_path = root / "vgg_transformer_config.yml"
        if not config_path.is_file():
            raise FileNotFoundError(f"vietocr config not found at {config_path}")
        if not weights_path.is_file():
            raise FileNotFoundError(f"vietocr weights not found at {weights_path}")

        from vietocr.tool.config import Cfg
        from vietocr.tool.predictor import Predictor

        cfg = Cfg.load_config_from_file(str(config_path))
        cfg["weights"] = str(weights_path)
        cfg["device"] = "cpu"
        cfg["cnn"]["pretrained"] = False
        cfg["predictor"]["beamsearch"] = False
        self._predictor = Predictor(cfg)
        self._detector = detector

    def read_array(self, image: np.ndarray) -> tuple[list[str], list[float]]:
        boxes = self._detector.detect_boxes(image)
        lines: list[str] = []
        scores: list[float] = []
        for box in boxes:
            crop = _crop_box(image, np.asarray(box))
            if crop.size == 0:
                continue
            text, prob = self._predictor.predict(Image.fromarray(crop), return_prob=True)
            text = text.strip()
            if text:
                lines.append(text)
                scores.append(float(prob))
        return lines, scores

    def read(self, payload: bytes) -> tuple[list[str], list[float]]:
        return self.read_array(decode_image(payload))

    def inspect_document(self, payload: bytes) -> dict[str, Any]:
        lines, scores = self.read(payload)
        return {
            "status": "OK" if lines else "INCONCLUSIVE",
            "engine": "vietocr-vgg-transformer+rapidocr-det",
            "line_count": len(lines),
            "mean_confidence": round(float(np.mean(scores)), 6) if scores else None,
            "lines": lines,
        }
