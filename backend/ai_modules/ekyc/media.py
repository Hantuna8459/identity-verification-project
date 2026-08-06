from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import httpx
import numpy as np

from ai_modules.ekyc.errors import InvalidEvidenceError

# Cross-cutting media helpers shared by more than one capability - not itself
# a capability, so it doesn't get a capability-named file.


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


def crop(image: np.ndarray, bbox: np.ndarray, scale: float = 1.0) -> np.ndarray:
    x1, y1, x2, y2 = [float(value) for value in bbox]
    center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
    width, height = (x2 - x1) * scale, (y2 - y1) * scale
    left = max(0, round(center_x - width / 2))
    top = max(0, round(center_y - height / 2))
    right = min(image.shape[1], round(center_x + width / 2))
    bottom = min(image.shape[0], round(center_y + height / 2))
    cropped = image[top:bottom, left:right]
    if cropped.size == 0:
        raise InvalidEvidenceError("Empty face crop")
    return cropped


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


def video_metadata(media_path: Path) -> dict[str, float | int | None]:
    capture = cv2.VideoCapture(str(media_path))
    if not capture.isOpened():
        raise InvalidEvidenceError("Evidence is not a decodable video")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_ms = (frame_count / fps * 1000.0) if fps > 0.0 and frame_count > 0 else None
    capture.release()
    return {
        "fps": fps if fps > 0.0 else None,
        "frame_count": frame_count if frame_count > 0 else None,
        "duration_ms": duration_ms,
    }


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
