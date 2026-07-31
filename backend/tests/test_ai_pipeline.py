from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from ai_modules.ekyc.anti_spoof import inspect_camera_injection, inspect_replay_attack
from ai_modules.ekyc.mrz import inspect_td3
from ai_modules.ekyc.runtime import inspect_head_turn_sequence
from app.adapters.analyzer import OfflineModelAnalyzer


def test_icao_td3_check_digits_are_valid_without_exposing_mrz() -> None:
    result = inspect_td3(
        [
            "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<",
            "L898902C36UTO7408122F1204159ZE184226B<<<<<10",
        ]
    )

    assert result["status"] == "OK"
    assert result["all_check_digits_valid"] is True
    assert "lines" not in result


def test_analyzer_readiness_checks_every_grouped_artifact(tmp_path: Path) -> None:
    models = tmp_path / "models"
    models.mkdir()
    (models / "one.bin").write_bytes(b"one")
    manifest = {
        "models": [
            {
                "id": "group",
                "required": True,
                "approval_status": "evaluation_only",
                "usage_scope": ["technical_demo"],
                "artifacts": [
                    {
                        "path": "one.bin",
                        "size_bytes": 3,
                        "sha256": (
                            "7692c3ad3540bb803c020b3aee66cd8887123234ea0c6e7143c0add73ff431ed"
                        ),
                    },
                    {
                        "path": "missing.bin",
                        "size_bytes": 1,
                        "sha256": "0" * 64,
                    },
                ],
            },
            {
                "id": "quarantined",
                "required": True,
                "approval_status": "quarantined",
                "usage_scope": [],
                "path": "ignored.bin",
                "size_bytes": 1,
                "sha256": "0" * 64,
            },
        ]
    }
    (models / "manifest.json").write_text(json.dumps(manifest))

    readiness = OfflineModelAnalyzer(models, True).readiness()

    assert readiness["ready"] is False
    assert readiness["models"] == ["group"]
    assert readiness["invalid"] == ["group:missing.bin:missing"]


def test_model_downloader_rejects_archive_traversal() -> None:
    script = Path(__file__).parents[2] / "scripts/models.py"
    spec = importlib.util.spec_from_file_location("model_downloader", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with pytest.raises(RuntimeError, match="Unsafe archive member"):
        module._safe_member("../secret")


def test_head_turn_sequence_requires_both_turns_and_return_to_center() -> None:
    result = inspect_head_turn_sequence([0.01, 0.18, 0.02, -0.2, 0.01])

    assert result["status"] == "OK"
    assert result["sequence_complete"] is True
    assert result["completed_step_count"] == result["required_step_count"] == 5


def test_head_turn_sequence_is_inconclusive_when_user_skips_a_turn() -> None:
    result = inspect_head_turn_sequence([0.01, 0.2, 0.02, 0.19, 0.01])

    assert result["status"] == "INCONCLUSIVE"
    assert result["sequence_complete"] is False
    assert result["reason"] == "CHALLENGE_SEQUENCE_INCOMPLETE"
    assert "yaw_samples" not in result


def test_replay_heuristic_flags_duplicate_frames() -> None:
    frame = np.zeros((96, 96, 3), dtype=np.uint8)
    frame[20:76, 20:76] = 180
    result = inspect_replay_attack([frame.copy() for _ in range(8)])

    assert result["status"] == "OK"
    assert result["confirmed"] is True
    assert result["suspicious"] is True
    assert result["duplicate_pairs"] > 0


def test_replay_heuristic_does_not_flag_moving_frames() -> None:
    frames = []
    for offset in range(8):
        frame = np.zeros((96, 96, 3), dtype=np.uint8)
        frame[20:76, 20 + offset * 6 : 76 + offset * 6] = 180
        frames.append(frame)
    result = inspect_replay_attack(frames)

    assert result["suspicious"] is False


def test_camera_injection_heuristic_exposes_metadata_and_timing_signals() -> None:
    frame = np.zeros((96, 96, 3), dtype=np.uint8)
    replay = inspect_replay_attack([frame.copy() for _ in range(8)])
    result = inspect_camera_injection(
        frames=[frame] * 8,
        fps=None,
        frame_count=None,
        duration_ms=500.0,
        active_liveness={"sequence_complete": False, "sampled_pose_count": 2},
        replay=replay,
    )

    assert result["suspicious"] is True
    assert "VIDEO_METADATA_ANOMALY" in result["reason_codes"]
    assert "CHALLENGE_TIMING_ANOMALY" in result["reason_codes"]


def test_model_output_separates_execution_from_review_signal() -> None:
    normalized = OfflineModelAnalyzer.normalize_capabilities(
        {
            "face_match": {
                "status": "OK",
                "engine": "face-test",
                "cosine_similarity": -0.019026,
                "sampled_frames": 12,
                "frames_with_face": 1,
            },
            "voice_challenge": {
                "status": "OK",
                "challenge_length": 6,
                "recognized_digit_count": 1,
                "similarity": 0.166667,
            },
            "lip_sync": {
                "status": "OK",
                "verdict": "fake",
                "confidence": 0.1117,
                "manipulation_probability": 0.8929,
            },
        }
    )

    assert normalized["face_match"]["execution_status"] == "COMPLETED"
    assert normalized["face_match"]["review_signal"] == "SCORE_AVAILABLE"
    assert normalized["face_match"]["threshold"] == {
        "value": None,
        "approval_status": "NOT_APPROVED",
    }
    assert normalized["voice_challenge"]["review_signal"] == "CHALLENGE_MISMATCH"
    assert "VOICE_CHALLENGE_MISMATCH" in normalized["voice_challenge"]["reason_codes"]
    assert normalized["lip_sync"]["review_signal"] == "SUSPICIOUS"


def test_model_output_marks_incomplete_active_liveness_challenge() -> None:
    normalized = OfflineModelAnalyzer.normalize_capabilities(
        {
            "active_liveness": {
                "status": "INCONCLUSIVE",
                "sequence_complete": False,
                "completed_step_count": 3,
                "required_step_count": 5,
                "reason": "CHALLENGE_SEQUENCE_INCOMPLETE",
            }
        }
    )

    assert normalized["active_liveness"]["execution_status"] == "INCONCLUSIVE"
    assert normalized["active_liveness"]["review_signal"] == "CHALLENGE_INCOMPLETE"
    assert normalized["active_liveness"]["reason_codes"] == ["CHALLENGE_SEQUENCE_INCOMPLETE"]


def test_model_output_preserves_unavailable_ocr_without_false_success() -> None:
    normalized = OfflineModelAnalyzer.normalize_capabilities(
        {"ocr": {"status": "UNAVAILABLE", "reason": "REQUIRED_MODEL_ARTIFACT_INVALID"}}
    )

    assert normalized["ocr"]["execution_status"] == "UNAVAILABLE"
    assert normalized["ocr"]["review_signal"] == "UNAVAILABLE"
