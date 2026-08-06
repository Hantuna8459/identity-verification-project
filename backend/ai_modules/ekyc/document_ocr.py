from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
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

    def read_array(self, image: np.ndarray) -> tuple[list[str], list[float]]:
        output: Any = self._engine(image)
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
