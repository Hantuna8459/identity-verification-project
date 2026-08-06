from __future__ import annotations

import json
import re
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

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
