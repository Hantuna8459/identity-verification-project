from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import av
from vosk import KaldiRecognizer, Model, SetLogLevel


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
        recognizer = KaldiRecognizer(self._model, 16000)
        text_parts: list[str] = []
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        with av.open(str(media_path)) as container:
            stream = container.streams.audio[0]
            for frame in container.decode(stream):
                for resampled in resampler.resample(frame):
                    if recognizer.AcceptWaveform(resampled.to_ndarray().tobytes()):
                        text_parts.append(json.loads(recognizer.Result()).get("text", ""))
        for resampled in resampler.resample(None):
            if recognizer.AcceptWaveform(resampled.to_ndarray().tobytes()):
                text_parts.append(json.loads(recognizer.Result()).get("text", ""))
        text_parts.append(json.loads(recognizer.FinalResult()).get("text", ""))
        transcript = " ".join(text_parts)
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
