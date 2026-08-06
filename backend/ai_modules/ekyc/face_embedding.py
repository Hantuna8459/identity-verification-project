from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from ai_modules.ekyc.errors import InvalidEvidenceError


class ArcFaceEmbedder:
    _TEMPLATE = np.array(
        [
            [38.2946, 51.6963],
            [73.5318, 51.5014],
            [56.0252, 71.7366],
            [41.5493, 92.3655],
            [70.7299, 92.2041],
        ],
        dtype=np.float32,
    )

    def __init__(self, model_dir: Path) -> None:
        providers = ["CPUExecutionProvider"]
        root = model_dir / "insightface/models/buffalo_l"
        self._embedder = ort.InferenceSession(str(root / "w600k_r50.onnx"), providers=providers)
        self._embedder_input = self._embedder.get_inputs()[0].name

    def embedding(self, image: np.ndarray, landmarks: np.ndarray) -> np.ndarray:
        transform, _ = cv2.estimateAffinePartial2D(landmarks.astype(np.float32), self._TEMPLATE)
        if transform is None:
            raise InvalidEvidenceError("Face alignment failed")
        aligned = cv2.warpAffine(image, transform, (112, 112), borderValue=0)
        blob = cv2.dnn.blobFromImage(aligned, 1 / 127.5, (112, 112), (127.5,) * 3, swapRB=True)
        embedding = np.asarray(
            self._embedder.run(None, {self._embedder_input: blob})[0], dtype=np.float32
        ).reshape(-1)
        return embedding / max(float(np.linalg.norm(embedding)), 1e-12)
