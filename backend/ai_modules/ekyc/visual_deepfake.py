from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from ai_modules.ekyc.media import crop, softmax


class DeepfakeEngine:
    def __init__(self, model_dir: Path) -> None:
        providers = ["CPUExecutionProvider"]
        self._session = ort.InferenceSession(
            str(model_dir / "deepfake_detector.onnx"), providers=providers
        )

    def deepfake(self, image: np.ndarray, bbox: np.ndarray) -> float:
        face = cv2.cvtColor(cv2.resize(crop(image, bbox, 1.3), (224, 224)), cv2.COLOR_BGR2RGB)
        tensor = face.astype(np.float32) / 255.0
        tensor = (tensor - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
        tensor = np.transpose(tensor, (2, 0, 1))[None, ...].astype(np.float32)
        input_meta = self._session.get_inputs()[0]
        output = self._session.run(None, {input_meta.name: tensor})[0]
        probabilities = softmax(output)
        return float(probabilities[0])
