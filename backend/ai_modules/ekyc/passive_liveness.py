from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from ai_modules.ekyc.media import crop, softmax


class MiniFasNetEngine:
    def __init__(self, model_dir: Path) -> None:
        providers = ["CPUExecutionProvider"]
        self._session = ort.InferenceSession(
            str(model_dir / "minifasnet.onnx"), providers=providers
        )

    def liveness(self, image: np.ndarray, bbox: np.ndarray) -> float:
        face = cv2.resize(crop(image, bbox, 2.7), (80, 80)).astype(np.float32)
        tensor = np.transpose(face, (2, 0, 1))[None, ...]
        input_name = self._session.get_inputs()[0].name
        output = self._session.run(None, {input_name: tensor})[0]
        probabilities = softmax(output)
        return float(probabilities[1] if probabilities.size > 1 else probabilities[0])
