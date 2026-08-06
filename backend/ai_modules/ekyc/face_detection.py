from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from ai_modules.ekyc.errors import InvalidEvidenceError


class ScrfdFaceDetector:
    def __init__(self, model_dir: Path) -> None:
        providers = ["CPUExecutionProvider"]
        root = model_dir / "insightface/models/buffalo_l"
        self._detector = ort.InferenceSession(str(root / "det_10g.onnx"), providers=providers)
        self._detector_input = self._detector.get_inputs()[0].name

    @staticmethod
    def _distance_to_bbox(points: np.ndarray, distance: np.ndarray) -> np.ndarray:
        return np.column_stack(
            (
                points[:, 0] - distance[:, 0],
                points[:, 1] - distance[:, 1],
                points[:, 0] + distance[:, 2],
                points[:, 1] + distance[:, 3],
            )
        )

    def detect(self, image: np.ndarray) -> list[dict[str, np.ndarray | float]]:
        height, width = image.shape[:2]
        scale = min(640 / width, 640 / height)
        resized = cv2.resize(image, (round(width * scale), round(height * scale)))
        canvas = np.zeros((640, 640, 3), dtype=np.uint8)
        canvas[: resized.shape[0], : resized.shape[1]] = resized
        blob = cv2.dnn.blobFromImage(canvas, 1 / 128.0, (640, 640), (127.5,) * 3, swapRB=True)
        outputs = self._detector.run(None, {self._detector_input: blob})
        candidates: list[dict[str, np.ndarray | float]] = []
        for index, stride in enumerate((8, 16, 32)):
            scores = np.asarray(outputs[index]).reshape(-1)
            boxes = np.asarray(outputs[index + 3]).reshape(-1, 4) * stride
            landmarks = np.asarray(outputs[index + 6]).reshape(-1, 10) * stride
            feature_h = 640 // stride
            feature_w = 640 // stride
            grid_y, grid_x = np.mgrid[:feature_h, :feature_w]
            centers = np.column_stack((grid_x.ravel(), grid_y.ravel())).astype(np.float32)
            centers *= stride
            centers = np.repeat(centers, 2, axis=0)
            keep = np.where(scores >= 0.5)[0]
            decoded = self._distance_to_bbox(centers, boxes)
            for item in keep:
                point = landmarks[item].reshape(5, 2) + np.tile(centers[item], (5, 1))
                candidates.append(
                    {
                        "score": float(scores[item]),
                        "bbox": decoded[item] / scale,
                        "landmarks": point / scale,
                    }
                )
        candidates.sort(key=lambda value: float(value["score"]), reverse=True)
        selected: list[dict[str, np.ndarray | float]] = []
        for candidate in candidates:
            box = np.asarray(candidate["bbox"])
            if all(self._iou(box, np.asarray(existing["bbox"])) < 0.4 for existing in selected):
                selected.append(candidate)
        return selected

    @staticmethod
    def _iou(first: np.ndarray, second: np.ndarray) -> float:
        x1, y1 = np.maximum(first[:2], second[:2])
        x2, y2 = np.minimum(first[2:], second[2:])
        intersection = max(0.0, float(x2 - x1)) * max(0.0, float(y2 - y1))
        first_area = max(0.0, float(first[2] - first[0])) * max(0.0, float(first[3] - first[1]))
        second_area = max(0.0, float(second[2] - second[0])) * max(
            0.0, float(second[3] - second[1])
        )
        return intersection / max(first_area + second_area - intersection, 1e-6)

    def best_face(self, image: np.ndarray) -> dict[str, np.ndarray | float]:
        faces = self.detect(image)
        if not faces:
            raise InvalidEvidenceError("No face detected")
        return max(
            faces,
            key=lambda face: float(
                (np.asarray(face["bbox"])[2] - np.asarray(face["bbox"])[0])
                * (np.asarray(face["bbox"])[3] - np.asarray(face["bbox"])[1])
            ),
        )
