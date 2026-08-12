from __future__ import annotations

import tempfile
from pathlib import Path

import cv2
import numpy as np


def tiny_jpeg_bytes(size: int = 16, color: tuple[int, int, int] = (0, 0, 0)) -> bytes:
    """Genuinely decodable single-color JPEG bytes (real cv2.imencode()), not
    a placeholder byte string - ai_modules.ekyc.media.decode_image() runs
    real cv2.imdecode() even when the capability providers around it are
    faked, so fixtures must actually decode."""
    image = np.full((size, size, 3), color, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError("failed to encode tiny JPEG fixture")
    return encoded.tobytes()


def tiny_mp4_bytes(frame_count: int = 5, fps: float = 5.0, size: int = 16) -> bytes:
    """Genuinely decodable MP4 bytes (via cv2.VideoWriter) - real
    cv2.VideoCapture() reads these back, same reason as tiny_jpeg_bytes()."""
    frame = np.zeros((size, size, 3), dtype=np.uint8)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tiny.mp4"
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (size, size))
        try:
            for _ in range(frame_count):
                writer.write(frame)
        finally:
            writer.release()
        return path.read_bytes()
