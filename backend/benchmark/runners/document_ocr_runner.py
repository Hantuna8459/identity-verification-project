from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from ai_modules.ekyc.document_ocr import LocalOcr
from benchmark import dataset_registry, metrics, report
from benchmark.engines.vietocr_engine import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_WEIGHTS_PATH,
    VietocrEngine,
)
from benchmark.fixtures.ocr_fixtures import generate_ocr_samples

CAPABILITY = "document_ocr"
DATASET_ID = "synthetic-document-ocr-smoke-v1"
PROVIDER_ID = "rapidocr-ppocrv6-small"
VIETOCR_MODEL_ID = "vietocr-vgg-transformer"


def _run_rapidocr(model_dir: Path, samples: list) -> tuple[dict[str, Any], list[float]]:
    ocr = LocalOcr(model_dir)
    latencies: list[float] = []
    cers: list[float] = []
    wers: list[float] = []
    excluded = 0
    for sample in samples:
        start = perf_counter()
        predicted_lines, _scores = ocr.read_array(sample.image)
        latencies.append((perf_counter() - start) * 1000)
        if len(predicted_lines) != len(sample.ground_truth_lines):
            excluded += 1
            continue
        for ground_truth, predicted in zip(sample.ground_truth_lines, predicted_lines, strict=True):
            cers.append(metrics.cer(ground_truth, predicted))
            wers.append(metrics.wer(ground_truth, predicted))
    metrics_out = {
        "cer_mean": metrics.mean(cers),
        "wer_mean": metrics.mean(wers),
        "lines_scored": len(cers),
        "line_count_mismatch_rate": excluded / len(samples) if samples else None,
        "excluded_count": excluded,
    }
    return metrics_out, latencies


def _run_vietocr_candidate(model_dir: Path, samples: list) -> dict[str, Any]:
    entry_id = VIETOCR_MODEL_ID
    weights_path = model_dir / DEFAULT_WEIGHTS_PATH
    config_path = model_dir / DEFAULT_CONFIG_PATH
    if not weights_path.is_file() or not config_path.is_file():
        return {
            "engine_id": entry_id,
            "status": "SKIPPED",
            "reason": (
                "local artifacts not present on this machine; run 'python "
                "scripts/models.py --profile benchmark_only --include "
                "vietocr-vgg-transformer' first"
            ),
        }

    engine = VietocrEngine(weights_path, config_path)
    latencies: list[float] = []
    cers: list[float] = []
    wers: list[float] = []
    for sample in samples:
        for ground_truth, crop in zip(sample.ground_truth_lines, sample.line_crops, strict=True):
            start = perf_counter()
            predicted, _confidence = engine.read_line(crop)
            latencies.append((perf_counter() - start) * 1000)
            cers.append(metrics.cer(ground_truth, predicted))
            wers.append(metrics.wer(ground_truth, predicted))

    return {
        "engine_id": entry_id,
        "status": "SCORED",
        "metrics": {
            "cer_mean": metrics.mean(cers),
            "wer_mean": metrics.mean(wers),
            "lines_scored": len(cers),
        },
        "latency_ms": {
            "p50": metrics.percentile(latencies, 0.5),
            "p95": metrics.percentile(latencies, 0.95),
            "mean": metrics.mean(latencies),
        },
        "note": (
            "Line-level recognizer only (no text detection) - scored against "
            "the same known-good line crops, not full-page detection like "
            "RapidOCR; not directly comparable to a full pipeline error rate."
        ),
    }


def run(model_dir: Path, sample_count: int = 20, seed: int = 20260811) -> dict[str, Any]:
    dataset = dataset_registry.get_dataset(DATASET_ID, capability=CAPABILITY)
    samples, has_diacritics_font = generate_ocr_samples(sample_count, seed)

    metrics_out, latencies = _run_rapidocr(model_dir, samples)
    metrics_out["has_diacritics_font"] = has_diacritics_font
    vietocr_result = _run_vietocr_candidate(model_dir, samples)

    return report.build_report(
        capability=CAPABILITY,
        provider_id=PROVIDER_ID,
        model_id=PROVIDER_ID,
        dataset=dataset,
        sample_count=len(samples),
        excluded_count=metrics_out.pop("excluded_count"),
        metrics_out=metrics_out,
        latency_ms=latencies,
        candidate_engines=[vietocr_result],
        notes=(
            "Synthetic smoke subset only (rendered Vietnamese field text, not "
            "real documents). Primary metrics score RapidOCR's own full-page "
            "detect+recognize pipeline (now the document_ocr fallback "
            "provider, not primary - see models/manifest.json). "
            "candidate_engines scores vietocr-vgg-transformer as a "
            "line-level recognizer only, on the same known-good line crops - "
            "not the same thing as the production primary path, which pairs "
            "this recognizer with RapidOCR's detector "
            "(ai_modules/ekyc/document_ocr.py::VietOcr); a full-page "
            "detect+recognize benchmark for that hybrid pipeline does not "
            "exist yet. See models/manifest.json/"
            "docs/model_license_risk_matrix.html for vietocr's recorded "
            "license status. metrics.has_diacritics_font=false means the "
            "render font had no Vietnamese diacritic glyphs and this run "
            "does NOT test what it claims to."
        ),
    )
