from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

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
