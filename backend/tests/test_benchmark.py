from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmark import dataset_registry, metrics, quarantine
from benchmark.fixtures.mrz_fixtures import generate_mrz_samples
from benchmark.fixtures.ocr_fixtures import generate_ocr_samples
from benchmark.runners import passport_mrz_runner

MODEL_DIR = Path(__file__).resolve().parents[2] / "models"
_RAPIDOCR_PRESENT = (MODEL_DIR / "rapidocr" / "PP-OCRv6_det_small.onnx").exists()


def test_cer_wer_exact_match() -> None:
    assert metrics.cer("HELLO", "HELLO") == 0.0
    assert metrics.cer("HELLO", "HELLX") == pytest.approx(0.2)
    assert metrics.wer("SO 123", "SO 124") == pytest.approx(0.5)
    assert metrics.exact_match("A", "A")
    assert not metrics.exact_match("A", "B")


def test_wilson_interval_bounds() -> None:
    assert metrics.wilson_interval(0, 0) is None
    lo, hi = metrics.wilson_interval(10, 10)
    assert 0.0 < lo <= 1.0
    assert hi == 1.0


def test_dataset_registry_loads_expected_records() -> None:
    records = {record.dataset_id: record for record in dataset_registry.load_all()}
    assert "synthetic-document-ocr-smoke-v1" in records
    assert "synthetic-passport-mrz-smoke-v1" in records
    for record in records.values():
        assert record.approval_status == "approved_for_evaluation"
        assert record.sensitivity == "synthetic"


def test_dataset_registry_fails_closed_on_unapproved_dataset(tmp_path: Path) -> None:
    entry = dataset_registry.load_all()[0]
    tampered = dict(entry.__dict__)
    tampered.update(
        {
            "source_url": None,
            "license_name": None,
            "license_url": None,
            "terms_summary": "x",
            "distribution_permission": "allowed",
            "storage_location": "not_downloaded",
            "checksum_sha256": None,
            "approval_owner": "user",
            "approved_at": None,
            "expires_at": None,
            "notes": "",
            "approval_status": "candidate",
        }
    )
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps([tampered]), encoding="utf-8")

    with pytest.raises(RuntimeError, match="fail-closed"):
        dataset_registry.require_approved(
            tampered["dataset_id"], capability="document_ocr", registry_path=registry_path
        )


def test_dataset_registry_rejects_wrong_capability() -> None:
    with pytest.raises(RuntimeError, match="not registered for capability"):
        dataset_registry.require_approved(
            "synthetic-document-ocr-smoke-v1", capability="passport_mrz"
        )


def test_quarantine_no_longer_flags_vietocr_once_evaluation_only() -> None:
    """models/manifest.json: vietocr-vgg-transformer moved to
    evaluation_only/benchmark_only (owner-accepted risk, 2026-08-11) - no
    longer license-blocked, so it must not show up as skipped."""
    assert quarantine.skipped_models_for("document_ocr") == []


def test_quarantine_flags_a_genuinely_blocked_candidate(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "id": "vietocr-vgg-transformer",
                        "approval_status": "quarantined",
                        "license": "WEIGHT_LICENSE_REVIEW_REQUIRED",
                        "distribution_permission": "not-established",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    skipped = quarantine.skipped_models_for("document_ocr", manifest_path=manifest_path)
    assert [entry["model_id"] for entry in skipped] == ["vietocr-vgg-transformer"]
    assert skipped[0]["approval_status"] == "quarantined"


def test_quarantine_empty_for_unmapped_capability() -> None:
    assert quarantine.skipped_models_for("passport_mrz") == []


def test_mrz_fixtures_are_deterministic() -> None:
    first = generate_mrz_samples(20, seed=1)
    second = generate_mrz_samples(20, seed=1)
    assert [sample.lines for sample in first] == [sample.lines for sample in second]
    assert any(sample.defect is not None for sample in first)
    assert any(sample.defect is None for sample in first)


def test_ocr_fixtures_are_deterministic() -> None:
    first, has_diacritics_font_1 = generate_ocr_samples(5, seed=1)
    second, has_diacritics_font_2 = generate_ocr_samples(5, seed=1)
    assert [sample.ground_truth_lines for sample in first] == [
        sample.ground_truth_lines for sample in second
    ]
    assert first[0].image.shape == second[0].image.shape
    assert has_diacritics_font_1 == has_diacritics_font_2
    assert len(first[0].line_crops) == len(first[0].ground_truth_lines)


def test_passport_mrz_runner_report_shape() -> None:
    result = passport_mrz_runner.run(sample_count=20, seed=1)
    assert result["capability"] == "passport_mrz"
    assert result["sample_count"] == 20
    assert result["metrics"]["detection_accuracy"] > 0.8
    assert result["skipped_models"] == []


@pytest.mark.skipif(not _RAPIDOCR_PRESENT, reason="rapidocr model artifacts not downloaded locally")
def test_document_ocr_runner_report_shape() -> None:
    from benchmark.runners import document_ocr_runner

    result = document_ocr_runner.run(MODEL_DIR, sample_count=2, seed=1)
    assert result["capability"] == "document_ocr"
    assert result["sample_count"] == 2
    assert result["metrics"]["cer_mean"] is not None
    assert result["metrics"]["cer_mean"] < 0.2
    # vietocr-vgg-transformer is evaluation_only/benchmark_only, not
    # license-blocked, so it must never show up as governance-skipped.
    assert result["skipped_models"] == []
    assert len(result["candidate_engines"]) == 1
    vietocr_result = result["candidate_engines"][0]
    assert vietocr_result["engine_id"] == "vietocr-vgg-transformer"
    assert vietocr_result["status"] in {"SCORED", "SKIPPED"}
    if vietocr_result["status"] == "SCORED":
        assert vietocr_result["metrics"]["cer_mean"] is not None
