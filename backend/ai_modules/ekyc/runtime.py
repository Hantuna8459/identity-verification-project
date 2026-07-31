from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

import cv2
import httpx
import numpy as np
import onnxruntime as ort
from rapidocr import RapidOCR
from vosk import KaldiRecognizer, Model, SetLogLevel

from ai_modules.ekyc.mrz import inspect_td3


class InvalidEvidenceError(ValueError):
    pass


def decode_image(payload: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise InvalidEvidenceError("Evidence is not a decodable image")
    return image


def softmax(values: np.ndarray) -> np.ndarray:
    flat = np.asarray(values, dtype=np.float32).reshape(-1)
    shifted = flat - np.max(flat)
    exponential = np.exp(shifted)
    return exponential / np.sum(exponential)


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

    def read(self, payload: bytes) -> tuple[list[str], list[float]]:
        output: Any = self._engine(decode_image(payload))
        return list(output.txts or ()), [float(score) for score in (output.scores or ())]

    def inspect_document(self, payload: bytes, *, passport: bool) -> dict[str, Any]:
        lines, scores = self.read(payload)
        result: dict[str, Any] = {
            "status": "OK" if lines else "INCONCLUSIVE",
            "engine": "rapidocr-3.9.2/PP-OCRv6-small",
            "line_count": len(lines),
            "mean_confidence": round(float(np.mean(scores)), 6) if scores else None,
        }
        if passport:
            result["mrz"] = inspect_td3(lines)
        return result


class CccdLayoutOcr:
    def __init__(self, model_dir: Path) -> None:
        config_dir = model_dir / ".cache/ultralytics"
        config_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("YOLO_CONFIG_DIR", str(config_dir))
        from ultralytics import YOLO

        self._model = YOLO(str(model_dir / "cccd_layout_yolov11.pt"), task="detect")

    def inspect(self, payload: bytes, ocr: LocalOcr) -> dict[str, Any]:
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
            output: Any = ocr._engine(crop)
            line_count += len(output.txts or ())
            ocr_scores.extend(float(score) for score in (output.scores or ()))
        return {
            "status": "OK",
            "engine": "cccd-layout-yolov11+RapidOCR",
            "region_count": len(coordinates),
            "class_counts": class_counts,
            "ocr_line_count": line_count,
            "mean_ocr_confidence": round(float(np.mean(ocr_scores)), 6) if ocr_scores else None,
        }


class ScrfdArcFace:
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
        self._detector = ort.InferenceSession(str(root / "det_10g.onnx"), providers=providers)
        self._embedder = ort.InferenceSession(str(root / "w600k_r50.onnx"), providers=providers)
        self._detector_input = self._detector.get_inputs()[0].name
        self._embedder_input = self._embedder.get_inputs()[0].name

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


def estimate_head_yaw(landmarks: np.ndarray) -> float:
    """Estimate horizontal pose from SCRFD five-point landmarks."""
    points = np.asarray(landmarks, dtype=np.float32).reshape(5, 2)
    eye_distance = float(abs(points[1, 0] - points[0, 0]))
    if eye_distance <= 1e-6:
        raise InvalidEvidenceError("Face landmarks cannot estimate head pose")
    eye_center_x = float((points[0, 0] + points[1, 0]) / 2)
    return float((points[2, 0] - eye_center_x) / eye_distance)


def inspect_head_turn_sequence(yaw_samples: list[float]) -> dict[str, Any]:
    """Require center, opposite turns, then center without storing pose samples."""
    center_threshold = 0.08
    turn_threshold = 0.14
    phase = "initial_center"
    first_direction = 0
    completed_steps: list[str] = []

    for yaw in yaw_samples:
        centered = abs(yaw) <= center_threshold
        direction = -1 if yaw <= -turn_threshold else 1 if yaw >= turn_threshold else 0
        if phase == "initial_center" and centered:
            completed_steps.append("INITIAL_CENTER")
            phase = "first_turn"
        elif phase == "first_turn" and direction:
            first_direction = direction
            completed_steps.append("FIRST_TURN")
            phase = "center_between_turns"
        elif phase == "center_between_turns" and centered:
            completed_steps.append("CENTER_BETWEEN_TURNS")
            phase = "opposite_turn"
        elif phase == "opposite_turn" and direction == -first_direction:
            completed_steps.append("OPPOSITE_TURN")
            phase = "final_center"
        elif phase == "final_center" and centered:
            completed_steps.append("FINAL_CENTER")
            phase = "complete"
            break

    complete = phase == "complete"
    return {
        "status": "OK" if complete else "INCONCLUSIVE",
        "engine": "scrfd-5-point-head-pose-rules-v1",
        "sequence_complete": complete,
        "completed_step_count": len(completed_steps),
        "required_step_count": 5,
        "sampled_pose_count": len(yaw_samples),
        **({"reason": "CHALLENGE_SEQUENCE_INCOMPLETE"} if not complete else {}),
    }


class OnnxSignals:
    def __init__(self, model_dir: Path) -> None:
        providers = ["CPUExecutionProvider"]
        self._liveness = ort.InferenceSession(
            str(model_dir / "minifasnet.onnx"), providers=providers
        )
        self._deepfake = ort.InferenceSession(
            str(model_dir / "deepfake_detector.onnx"), providers=providers
        )

    @staticmethod
    def crop(image: np.ndarray, bbox: np.ndarray, scale: float = 1.0) -> np.ndarray:
        x1, y1, x2, y2 = [float(value) for value in bbox]
        center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
        width, height = (x2 - x1) * scale, (y2 - y1) * scale
        left = max(0, round(center_x - width / 2))
        top = max(0, round(center_y - height / 2))
        right = min(image.shape[1], round(center_x + width / 2))
        bottom = min(image.shape[0], round(center_y + height / 2))
        crop = image[top:bottom, left:right]
        if crop.size == 0:
            raise InvalidEvidenceError("Empty face crop")
        return crop

    def liveness(self, image: np.ndarray, bbox: np.ndarray) -> float:
        face = cv2.resize(self.crop(image, bbox, 2.7), (80, 80)).astype(np.float32)
        tensor = np.transpose(face, (2, 0, 1))[None, ...]
        input_name = self._liveness.get_inputs()[0].name
        output = self._liveness.run(None, {input_name: tensor})[0]
        probabilities = softmax(output)
        return float(probabilities[1] if probabilities.size > 1 else probabilities[0])

    def deepfake(self, image: np.ndarray, bbox: np.ndarray) -> float:
        face = cv2.cvtColor(cv2.resize(self.crop(image, bbox, 1.3), (224, 224)), cv2.COLOR_BGR2RGB)
        tensor = face.astype(np.float32) / 255.0
        tensor = (tensor - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
        tensor = np.transpose(tensor, (2, 0, 1))[None, ...].astype(np.float32)
        input_meta = self._deepfake.get_inputs()[0]
        output = self._deepfake.run(None, {input_meta.name: tensor})[0]
        probabilities = softmax(output)
        return float(probabilities[0])


class VoiceVerifier:
    _NUMBER_WORDS = {
        "không": "0",
        "mot": "1",
        "một": "1",
        "hai": "2",
        "ba": "3",
        "bon": "4",
        "bốn": "4",
        "tu": "4",
        "tư": "4",
        "nam": "5",
        "năm": "5",
        "sau": "6",
        "sáu": "6",
        "bay": "7",
        "bảy": "7",
        "tam": "8",
        "tám": "8",
        "chin": "9",
        "chín": "9",
    }

    def __init__(self, model_dir: Path, device: str) -> None:
        del device  # Vosk selects its CPU runtime internally.
        SetLogLevel(-1)
        self._model = Model(str(model_dir / "vosk/vosk-model-small-vn-0.4"))

    @classmethod
    def digits(cls, value: str) -> str:
        direct = "".join(re.findall(r"\d", value))
        if direct:
            return direct
        words = re.findall(r"[a-zA-ZÀ-ỹ]+", value.lower())
        return "".join(cls._NUMBER_WORDS.get(word, "") for word in words)

    def verify(self, media_path: Path, challenge: str) -> dict[str, Any]:
        wav_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as stream:
                wav_path = Path(stream.name)
            subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(media_path),
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-f",
                    "wav",
                    str(wav_path),
                ],
                check=True,
                timeout=120,
            )
            recognizer = KaldiRecognizer(self._model, 16000)
            text_parts: list[str] = []
            with wave.open(str(wav_path), "rb") as audio:
                while chunk := audio.readframes(4000):
                    if recognizer.AcceptWaveform(chunk):
                        text_parts.append(json.loads(recognizer.Result()).get("text", ""))
                text_parts.append(json.loads(recognizer.FinalResult()).get("text", ""))
            transcript = " ".join(text_parts)
        finally:
            if wav_path is not None:
                wav_path.unlink(missing_ok=True)
        expected, actual = self.digits(challenge), self.digits(transcript)
        distance = self._edit_distance(expected, actual)
        similarity = 1.0 - distance / max(len(expected), len(actual), 1)
        return {
            "status": "OK" if expected and actual else "INCONCLUSIVE",
            "engine": "vosk-model-small-vn-0.4",
            "challenge_length": len(expected),
            "recognized_digit_count": len(actual),
            "similarity": round(max(0.0, similarity), 6),
        }

    @staticmethod
    def _edit_distance(first: str, second: str) -> int:
        row = list(range(len(second) + 1))
        for first_index, first_value in enumerate(first, 1):
            next_row = [first_index]
            for second_index, second_value in enumerate(second, 1):
                next_row.append(
                    min(
                        next_row[-1] + 1,
                        row[second_index] + 1,
                        row[second_index - 1] + (first_value != second_value),
                    )
                )
            row = next_row
        return row[-1]


def video_frames(media_path: Path, maximum: int) -> list[np.ndarray]:
    capture = cv2.VideoCapture(str(media_path))
    if not capture.isOpened():
        raise InvalidEvidenceError("Evidence is not a decodable video")
    count = max(int(capture.get(cv2.CAP_PROP_FRAME_COUNT)), 1)
    indexes = np.linspace(0, count - 1, min(maximum, count), dtype=int)
    frames: list[np.ndarray] = []
    for index in indexes:
        capture.set(cv2.CAP_PROP_POS_FRAMES, int(index))
        success, frame = capture.read()
        if success and frame is not None:
            frames.append(frame)
    capture.release()
    if not frames:
        raise InvalidEvidenceError("Video contains no decodable frames")
    return frames


def call_lipsync(url: str, media_path: Path, content_type: str) -> dict[str, Any]:
    with media_path.open("rb") as stream:
        response = httpx.post(
            f"{url.rstrip('/')}/api/lip-sync",
            files={"video_file": (media_path.name, stream, content_type)},
            timeout=180,
        )
    response.raise_for_status()
    data = response.json()
    return {
        "status": "OK",
        "engine": "syncnet-v2/s3fd",
        "verdict": data.get("verdict"),
        "confidence": data.get("confidence"),
        "manipulation_probability": data.get("manipulation_probability"),
    }


def media_suffix(content_type: str) -> str:
    return {"video/webm": ".webm", "video/quicktime": ".mov"}.get(content_type, ".mp4")
