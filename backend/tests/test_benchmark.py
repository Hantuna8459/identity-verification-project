from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmark import dataset_registry, metrics
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
        assert record.sensitivity == "synthetic"


def test_get_dataset_ignores_legacy_status_fields(tmp_path: Path) -> None:
    """No approval workflow gates dataset usage anymore - get_dataset() only
    enforces that the dataset exists and is registered for the requested
    capability, regardless of any status-like field on the record."""
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
            "notes": "unreviewed - legal concern noted here",
        }
    )
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps([tampered]), encoding="utf-8")

    record = dataset_registry.get_dataset(
        tampered["dataset_id"], capability="document_ocr", registry_path=registry_path
    )
    assert record.dataset_id == tampered["dataset_id"]


def test_dataset_registry_rejects_unknown_dataset() -> None:
    with pytest.raises(RuntimeError, match="not found in dataset registry"):
        dataset_registry.get_dataset("does-not-exist", capability="document_ocr")


def test_dataset_registry_rejects_wrong_capability() -> None:
    with pytest.raises(RuntimeError, match="not registered for capability"):
        dataset_registry.get_dataset("synthetic-document-ocr-smoke-v1", capability="passport_mrz")


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
    # No governance gate excludes candidates anymore - skipped_models is only
    # ever populated by genuine capability-level skips, not license status.
    assert result["skipped_models"] == []
    assert len(result["candidate_engines"]) == 1
    vietocr_result = result["candidate_engines"][0]
    assert vietocr_result["engine_id"] == "vietocr-vgg-transformer"
    assert vietocr_result["status"] in {"SCORED", "SKIPPED"}
    if vietocr_result["status"] == "SCORED":
        assert vietocr_result["metrics"]["cer_mean"] is not None
