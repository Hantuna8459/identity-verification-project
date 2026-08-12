from __future__ import annotations

import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchmark import dataset_registry, metrics


def build_report(
    *,
    capability: str,
    provider_id: str,
    model_id: str | None,
    dataset: dataset_registry.DatasetRecord | dict[str, Any],
    sample_count: int,
    excluded_count: int,
    metrics_out: dict[str, Any],
    latency_ms: list[float],
    skipped_models: list[dict[str, Any]],
    candidate_engines: list[dict[str, Any]] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    # A plain dict is for real, non-distributable local evidence (e.g.
    # fieldcheck/local_cases/) that deliberately isn't registered in
    # dataset_registry.py - that registry's approval schema is for licensed,
    # distributable datasets, not a developer's own consented recordings.
    dataset_fields = (
        dataset_registry.as_report_fields(dataset)
        if isinstance(dataset, dataset_registry.DatasetRecord)
        else dataset
    )
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "capability": capability,
        "provider_id": provider_id,
        "model_id": model_id,
        "dataset": dataset_fields,
        "device": {
            "os": platform.platform(),
            "python": sys.version.split()[0],
            "cpu_count": os.cpu_count(),
        },
        "sample_count": sample_count,
        "excluded_count": excluded_count,
        "metrics": metrics_out,
        "latency_ms": {
            "p50": metrics.percentile(latency_ms, 0.5),
            "p95": metrics.percentile(latency_ms, 0.95),
            "mean": metrics.mean(latency_ms),
        },
        "skipped_models": skipped_models,
        "candidate_engines": candidate_engines or [],
        "notes": notes,
    }


def write_report(report: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = report["generated_at"].replace("+00:00", "Z").replace(":", "")
    path = out_dir / f"{report['capability']}_{stamp}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
