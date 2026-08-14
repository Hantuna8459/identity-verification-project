from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from ai_modules.ekyc.active_liveness import inspect_head_turn_sequence
from ai_modules.ekyc.camera_injection import inspect_camera_injection
from ai_modules.ekyc.passport_mrz import inspect_td3
from ai_modules.ekyc.replay_attack import inspect_replay_attack
from app.adapters.analyzer import OfflineModelAnalyzer
from app.adapters.capability_registry import CapabilityRegistry
from app.adapters.manifest import ManifestReader
from app.domain.capability_ports import FaceDetectionResult
from app.domain.document_fields import parse_layout_field, parse_layout_fields
from app.domain.face_matching import aggregate_face_similarities, select_face_match_candidates
from app.domain.threshold_decisions import (
    decide_face_match,
    decide_passive_liveness,
    decide_visual_deepfake,
)


def _empty_registry(model_dir: Path, profile: str = "technical_demo") -> CapabilityRegistry:
    """A registry with no chains/providers - enough to exercise
    OfflineModelAnalyzer.readiness()'s manifest-driven aggregate, which
    doesn't depend on any capability actually being registered."""
    return CapabilityRegistry(
        ManifestReader(model_dir, profile),
        {},
        {},
        timeout_seconds=5.0,
        circuit_failure_threshold=3,
        circuit_cooldown_seconds=60.0,
    )


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
                "id": "out-of-scope",
                "required": True,
                "usage_scope": [],
                "path": "ignored.bin",
                "size_bytes": 1,
                "sha256": "0" * 64,
            },
        ]
    }
    (models / "manifest.json").write_text(json.dumps(manifest))

    readiness = OfflineModelAnalyzer(_empty_registry(models), True).readiness()

    assert readiness["ready"] is False
    assert readiness["models"] == ["group"]
    assert readiness["invalid"] == ["group:missing.bin:missing"]


def _load_model_downloader() -> Any:
    script = Path(__file__).parents[2] / "scripts/models.py"
    spec = importlib.util.spec_from_file_location("model_downloader", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_model_downloader_rejects_archive_traversal() -> None:
    module = _load_model_downloader()

    with pytest.raises(RuntimeError, match="Unsafe archive member"):
        module._safe_member("../secret")


def test_runtime_manifest_strips_governance_only_fields(tmp_path: Path) -> None:
    """The lean manifest baked into the deployed image must keep only what
    ManifestReader reads at runtime - not vendor/license/source/purpose,
    which would otherwise ship inside the container image itself."""
    module = _load_model_downloader()
    manifest = {
        "schema_version": "1.2",
        "models": [
            {
                "id": "some-model",
                "purpose": "reveals exactly what this model does",
                "source": "vendor X",
                "source_repository": "https://example.com/vendor-x/model",
                "license": "PROPRIETARY",
                "revision": "v1",
                "required": True,
                "usage_scope": ["technical_demo"],
                "distribution_permission": "internal-demo-only",
                "notes": "AGENTS.md#x",
                "artifacts": [
                    {
                        "source_path": "vendor/weights.onnx",
                        "path": "weights.onnx",
                        "size_bytes": 10,
                        "sha256": "0" * 64,
                    }
                ],
            }
        ],
        "providers": [
            {
                "id": "some-provider",
                "capability": "passive_liveness",
                "model_id": "some-model",
                "adapter_spec_version": "ekyc-provider-adapter/1",
                "usage_scope": ["technical_demo"],
            }
        ],
    }

    output_path = tmp_path / "manifest.runtime.json"
    module.emit_runtime_manifest(manifest, output_path)
    lean = json.loads(output_path.read_text())

    model = lean["models"][0]
    assert model["id"] == "some-model"
    assert model["required"] is True
    assert model["artifacts"] == [{"path": "weights.onnx", "size_bytes": 10, "sha256": "0" * 64}]
    governance_only_fields = (
        "purpose",
        "source",
        "source_repository",
        "license",
        "distribution_permission",
        "notes",
    )
    for governance_only in governance_only_fields:
        assert governance_only not in model
    assert "source_path" not in model["artifacts"][0]

    provider = lean["providers"][0]
    assert provider == {
        "id": "some-provider",
        "usage_scope": ["technical_demo"],
    }


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


def test_face_match_selects_multiple_high_confidence_frames_with_a_limit() -> None:
    empty = np.zeros(5)
    candidates = [
        (np.full((1, 1, 3), index), FaceDetectionResult(score=score, bbox=empty, landmarks=empty))
        for index, score in enumerate([0.70, 0.95, 0.80, 0.90])
    ]

    selected = select_face_match_candidates(candidates, maximum=3)

    assert [candidate[1].score for candidate in selected] == [0.95, 0.90, 0.80]


def test_face_match_uses_median_to_resist_one_optimistic_frame() -> None:
    similarity = aggregate_face_similarities([0.41, 0.43, 0.98, 0.42, 0.44])

    assert similarity == pytest.approx(0.43)


def test_parse_layout_field_strips_bilingual_label_from_name() -> None:
    value = parse_layout_field("full_name", "Ho và tên I Full name: LUONG QUOC DOAN")

    assert value == "LUONG QUOC DOAN"


def test_parse_layout_field_extracts_date_regardless_of_label_noise() -> None:
    value = parse_layout_field("date_of_birth", "Ngày sinh / Date of birth: 30/05/2001")

    assert value == "30/05/2001"


def test_parse_layout_field_extracts_id_digits_from_ocr_noise() -> None:
    value = parse_layout_field("id_number", "sóINo.: 031201000716")

    assert value == "031201000716"


def test_parse_layout_field_leaves_mrz_unlabeled() -> None:
    raw = "IDVNM2010007163031201000716<<3 0105307M2605306VNM<<<<<<<<<<<8"

    assert parse_layout_field("mrz", raw) == raw


def test_parse_layout_field_falls_back_to_label_split_without_a_date_match() -> None:
    value = parse_layout_field("expiry_date", "Có giá trị đến / Date of expiry")

    assert value == "Có giá trị đến / Date of expiry"


def test_parse_layout_field_strips_semicolon_separated_label() -> None:
    # VietOCR sometimes reads the printed ':' as ';' - RapidOCR usually keeps it.
    value = parse_layout_field("full_name", "Họ và tên 1 Full name; LƯƠNG QUỐC ĐOÀN")

    assert value == "LƯƠNG QUỐC ĐOÀN"


def test_parse_layout_field_falls_back_to_label_keyword_without_any_separator() -> None:
    # VietOCR sometimes drops the separator entirely, leaving just a space
    # between the printed English label and the value.
    assert parse_layout_field("sex", "Giới tĩnh/Sex Nam") == "Nam"
    assert parse_layout_field("nationality", "Quốc tịch/Nationality Việt Nam") == "Việt Nam"


def test_parse_layout_fields_applies_per_field_rules_to_a_whole_dict() -> None:
    parsed = parse_layout_fields(
        {
            "sex": "Giói tinh / Sex: Nam",
            "issue_date": "Ngày, tháng, năm /Date, month, year: 29/09/2022",
        }
    )

    assert parsed == {"sex": "Nam", "issue_date": "29/09/2022"}


def test_decide_face_match_above_threshold_matches_with_no_reason_codes() -> None:
    decision, reason_codes = decide_face_match(0.5, match_threshold=0.45, consider_threshold=0.30)

    assert decision == "match"
    assert reason_codes == []


def test_decide_face_match_in_manual_review_band() -> None:
    decision, reason_codes = decide_face_match(0.35, match_threshold=0.45, consider_threshold=0.30)

    assert decision == "consider"
    assert reason_codes == ["FACE_MATCH_MANUAL_REVIEW_BAND"]


def test_decide_face_match_below_consider_threshold() -> None:
    decision, reason_codes = decide_face_match(0.1, match_threshold=0.45, consider_threshold=0.30)

    assert decision == "failed"
    assert reason_codes == ["FACE_MATCH_BELOW_CONSIDER_THRESHOLD"]


def test_decide_passive_liveness_above_threshold_is_live() -> None:
    decision, reason_codes = decide_passive_liveness(0.9, threshold=0.65, consider_threshold=0.45)

    assert decision == "match"
    assert reason_codes == []


def test_decide_passive_liveness_in_manual_review_band() -> None:
    decision, reason_codes = decide_passive_liveness(0.5, threshold=0.65, consider_threshold=0.45)

    assert decision == "consider"
    assert reason_codes == ["LIVENESS_MANUAL_REVIEW_BAND"]


def test_decide_passive_liveness_below_consider_threshold() -> None:
    decision, reason_codes = decide_passive_liveness(0.2, threshold=0.65, consider_threshold=0.45)

    assert decision == "failed"
    assert reason_codes == ["LIVENESS_BELOW_CONSIDER_THRESHOLD"]


def test_decide_visual_deepfake_below_threshold_is_clean() -> None:
    suspicious, reason_codes = decide_visual_deepfake(0.1, threshold=0.68)

    assert suspicious is False
    assert reason_codes == []


def test_decide_visual_deepfake_above_threshold_is_suspicious() -> None:
    suspicious, reason_codes = decide_visual_deepfake(0.9, threshold=0.68)

    assert suspicious is True
    assert reason_codes == ["DEEPFAKE_SUSPICIOUS_SCORE"]


def test_summary_reason_codes_flags_document_layout_unavailable_for_cccd() -> None:
    capabilities = {
        "ocr": {
            "documents": {
                "document_front": {
                    "execution_status": "COMPLETED",
                    "details": {"layout": {"execution_status": "UNAVAILABLE"}},
                },
                "document_back": {
                    "execution_status": "COMPLETED",
                    "details": {"layout": {"execution_status": "UNAVAILABLE"}},
                },
            }
        },
    }
    readiness = {"artifact_ready": True}

    codes = OfflineModelAnalyzer._summary_reason_codes(capabilities, readiness, statuses=[])

    assert "DOCUMENT_LAYOUT_UNAVAILABLE" in codes


def test_summary_reason_codes_does_not_flag_document_layout_when_healthy() -> None:
    capabilities = {
        "ocr": {
            "documents": {
                "document_front": {
                    "execution_status": "COMPLETED",
                    "details": {"layout": {"execution_status": "COMPLETED"}},
                },
            }
        },
    }
    readiness = {"artifact_ready": True}

    codes = OfflineModelAnalyzer._summary_reason_codes(capabilities, readiness, statuses=[])

    assert "DOCUMENT_LAYOUT_UNAVAILABLE" not in codes


def test_summary_reason_codes_does_not_flag_document_layout_for_passport() -> None:
    # Passports never populate "layout" at all - no document_layout model
    # for TD3 pages, see EkycOrchestrator.analyze().
    capabilities = {
        "ocr": {
            "documents": {
                "passport_page": {
                    "execution_status": "COMPLETED",
                    "details": {"mrz": {"execution_status": "COMPLETED"}},
                },
            }
        },
    }
    readiness = {"artifact_ready": True}

    codes = OfflineModelAnalyzer._summary_reason_codes(capabilities, readiness, statuses=[])

    assert "DOCUMENT_LAYOUT_UNAVAILABLE" not in codes


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
                "matched_frames": 1,
                "aggregation": "MEDIAN",
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
    assert normalized["face_match"]["review_signal"] == "ADVERSE_SIGNAL"
    assert normalized["face_match"]["threshold"] == {
        "value": None,
        "consider_threshold": None,
        "approval_status": "EVALUATION_ONLY",
    }
    assert normalized["face_match"]["details"]["matched_frames"] == 1
    assert normalized["face_match"]["details"]["aggregation"] == "MEDIAN"
    assert normalized["voice_challenge"]["review_signal"] == "CHALLENGE_MISMATCH"
    assert "VOICE_CHALLENGE_MISMATCH" in normalized["voice_challenge"]["reason_codes"]
    assert normalized["lip_sync"]["review_signal"] == "ADVERSE_SIGNAL"


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


def test_model_output_passes_through_attempts_provenance() -> None:
    attempts = [
        {
            "provider_id": "fake-primary",
            "provider_role": "primary",
            "status": "FAILED",
            "reason_codes": ["RuntimeError"],
        },
        {
            "provider_id": "fake-secondary",
            "provider_role": "secondary",
            "status": "COMPLETED",
            "reason_codes": [],
        },
    ]
    normalized = OfflineModelAnalyzer.normalize_capabilities(
        {
            "liveness": {
                "status": "OK",
                "engine": "fake-secondary",
                "live_probability": 0.9,
                "attempts": attempts,
            }
        }
    )

    assert normalized["liveness"]["attempts"] == attempts
    # A successful fallback must not be misread as a capability-level failure.
    assert normalized["liveness"]["execution_status"] == "COMPLETED"


def test_model_output_derives_reason_codes_from_failed_attempts() -> None:
    attempts = [
        {
            "provider_id": "fake-primary",
            "provider_role": "primary",
            "status": "UNAVAILABLE",
            "reason_codes": ["REQUIRED_MODEL_ARTIFACT_INVALID"],
        }
    ]
    normalized = OfflineModelAnalyzer.normalize_capabilities(
        {"liveness": {"status": "UNAVAILABLE", "attempts": attempts}}
    )

    assert normalized["liveness"]["execution_status"] == "UNAVAILABLE"
    assert normalized["liveness"]["reason_codes"] == ["REQUIRED_MODEL_ARTIFACT_INVALID"]


def test_collect_statuses_ignores_attempt_level_status() -> None:
    """A capability that succeeded via fallback must not leak its failed
    attempt's UNAVAILABLE/FAILED status into the top-level rollup."""
    capabilities = OfflineModelAnalyzer.normalize_capabilities(
        {
            "liveness": {
                "status": "OK",
                "live_probability": 0.9,
                "attempts": [
                    {"status": "UNAVAILABLE", "reason_codes": []},
                    {"status": "COMPLETED", "reason_codes": []},
                ],
            }
        }
    )

    statuses = OfflineModelAnalyzer._collect_statuses(capabilities)

    assert "UNAVAILABLE" not in statuses
    assert "COMPLETED" in statuses
