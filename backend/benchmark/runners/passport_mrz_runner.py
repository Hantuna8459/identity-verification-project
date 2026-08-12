from __future__ import annotations

from time import perf_counter
from typing import Any

from ai_modules.ekyc.passport_mrz import inspect_td3
from benchmark import dataset_registry, metrics, quarantine, report
from benchmark.fixtures.mrz_fixtures import generate_mrz_samples

CAPABILITY = "passport_mrz"
DATASET_ID = "synthetic-passport-mrz-smoke-v1"
PROVIDER_ID = "icao-td3-rules"


def run(sample_count: int = 40, seed: int = 20260811) -> dict[str, Any]:
    dataset = dataset_registry.require_approved(DATASET_ID, capability=CAPABILITY)
    samples = generate_mrz_samples(sample_count, seed)

    latencies: list[float] = []
    matches = 0
    exact_matches = 0
    valid_count = 0
    for sample in samples:
        start = perf_counter()
        result = inspect_td3(sample.lines)
        latencies.append((perf_counter() - start) * 1000)
        if result["status"] == sample.expected_status:
            matches += 1
        if sample.defect is None:
            valid_count += 1
            if (
                result.get("mrz_detected")
                and result.get("line_lengths") == [44, 44]
                and result["status"] == "OK"
            ):
                exact_matches += 1

    total = len(samples)
    metrics_out = {
        "detection_accuracy": matches / total if total else None,
        "detection_accuracy_ci95": metrics.wilson_interval(matches, total),
        "valid_sample_exact_match_rate": (exact_matches / valid_count) if valid_count else None,
        "defect_ratio": (total - valid_count) / total if total else None,
    }
    return report.build_report(
        capability=CAPABILITY,
        provider_id=PROVIDER_ID,
        model_id=None,
        dataset=dataset,
        sample_count=total,
        excluded_count=0,
        metrics_out=metrics_out,
        latency_ms=latencies,
        skipped_models=quarantine.skipped_models_for(CAPABILITY),
        notes="Synthetic TD3 line pairs, rule-based check-digit path only (no OCR/image involved).",
    )
