from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from support.tiny_media import tiny_mp4_bytes

from benchmark import report
from benchmark.dataset_registry import load_all
from benchmark.runners import lip_sync_runner, voice_challenge_runner


class _FakeVerifier:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, str]] = []

    def verify(self, media_path: Path, challenge: str) -> dict[str, Any]:
        self.calls.append((media_path, challenge))
        return {
            "status": "OK",
            "engine": "fake-vosk",
            "challenge_length": len(challenge),
            "recognized_digit_count": len(challenge),
            "similarity": 1.0,
        }


class _FakePredictorResult:
    def __init__(self, verdict: str, confidence: float) -> None:
        self.verdict = verdict
        self.confidence = confidence


class _FakePredictor:
    def __init__(self, verdict: str = "real", confidence: float = 0.9) -> None:
        self._verdict = verdict
        self._confidence = confidence
        self.calls: list[bytes] = []

    def predict_video_bytes(self, video_bytes: bytes, *, suffix: str) -> _FakePredictorResult:
        self.calls.append(video_bytes)
        return _FakePredictorResult(self._verdict, self._confidence)


def _write_case(
    case_dir: Path, *, voice_challenge: str | None = "1 2 3", with_video: bool = True
) -> None:
    case_dir.mkdir(parents=True)
    (case_dir / "document_front.jpg").write_bytes(b"not-a-real-image-not-decoded-by-these-runners")
    if with_video:
        (case_dir / "selfie_video.mp4").write_bytes(tiny_mp4_bytes())
    sidecar: dict[str, Any] = {}
    if voice_challenge is not None:
        sidecar["voice_challenge"] = voice_challenge
    if sidecar:
        (case_dir / "case.json").write_text(json.dumps(sidecar))


def test_voice_challenge_runner_empty_cases_root_is_a_scaffold(tmp_path: Path) -> None:
    result = voice_challenge_runner.run(tmp_path / "models", tmp_path / "does-not-exist")

    assert result["capability"] == "voice_challenge"
    assert result["sample_count"] == 0
    assert result["metrics"]["cases_evaluated"] == 0
    assert "0 samples" in result["notes"]
    assert result["dataset"]["dataset_id"] == "fieldcheck-local-cases"
    assert result["dataset"]["sensitivity"] == "real_pii"


def test_voice_challenge_runner_skips_cases_missing_video_or_challenge(tmp_path: Path) -> None:
    cases_root = tmp_path / "cases"
    _write_case(cases_root / "no-video", with_video=False)
    _write_case(cases_root / "no-challenge", voice_challenge=None)

    result = voice_challenge_runner.run(
        tmp_path / "models", cases_root, verifier=_FakeVerifier()
    )

    assert result["sample_count"] == 0
    reasons = {entry["reason"] for entry in result["metrics"]["skipped_cases"]}
    assert reasons == {"no selfie_video", "no voice_challenge in case.json"}


def test_voice_challenge_runner_scores_usable_cases_via_injected_verifier(tmp_path: Path) -> None:
    cases_root = tmp_path / "cases"
    _write_case(cases_root / "case-1", voice_challenge="1 2 3")
    _write_case(cases_root / "case-2", voice_challenge="4 5 6")
    fake = _FakeVerifier()

    result = voice_challenge_runner.run(tmp_path / "models", cases_root, verifier=fake)

    assert result["sample_count"] == 2
    assert len(fake.calls) == 2
    assert {challenge for _path, challenge in fake.calls} == {"1 2 3", "4 5 6"}
    assert result["metrics"]["similarity_mean"] == 1.0
    assert result["metrics"]["ok_rate"] == 1.0


def test_lip_sync_runner_empty_cases_root_is_a_scaffold(tmp_path: Path) -> None:
    result = lip_sync_runner.run(
        tmp_path / "models", tmp_path / "does-not-exist", predictor=_FakePredictor()
    )

    assert result["capability"] == "lip_sync"
    assert result["sample_count"] == 0
    assert "0 samples" in result["notes"]


def test_lip_sync_runner_missing_weights_is_skipped_not_raised(tmp_path: Path) -> None:
    empty_model_dir = tmp_path / "models"
    empty_model_dir.mkdir()

    result = lip_sync_runner.run(empty_model_dir, tmp_path / "does-not-exist")

    assert result["sample_count"] == 0
    assert result["skipped_models"][0]["model_id"] == "syncnet-v2"
    assert "weights not found" in result["skipped_models"][0]["reason"]


def test_lip_sync_runner_counts_verdicts_via_injected_predictor(tmp_path: Path) -> None:
    cases_root = tmp_path / "cases"
    _write_case(cases_root / "case-1")
    _write_case(cases_root / "case-2")
    fake = _FakePredictor(verdict="real", confidence=0.8)

    result = lip_sync_runner.run(tmp_path / "models", cases_root, predictor=fake)

    assert result["sample_count"] == 2
    assert len(fake.calls) == 2
    assert result["metrics"]["verdict_counts"] == {"real": 2}
    assert result["metrics"]["confidence_mean"] == 0.8


def test_build_report_accepts_plain_dict_dataset() -> None:
    plain_dataset = {"dataset_id": "x", "sensitivity": "real_pii"}

    result = report.build_report(
        capability="voice_challenge",
        provider_id="p",
        model_id=None,
        dataset=plain_dataset,
        sample_count=0,
        excluded_count=0,
        metrics_out={},
        latency_ms=[],
        skipped_models=[],
    )

    assert result["dataset"] == plain_dataset


def test_build_report_still_accepts_dataset_record() -> None:
    record = load_all()[0]

    result = report.build_report(
        capability=record.capabilities[0],
        provider_id="p",
        model_id=None,
        dataset=record,
        sample_count=0,
        excluded_count=0,
        metrics_out={},
        latency_ms=[],
        skipped_models=[],
    )

    assert result["dataset"]["dataset_id"] == record.dataset_id
