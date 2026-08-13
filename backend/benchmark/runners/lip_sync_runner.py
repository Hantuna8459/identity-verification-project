from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any, Protocol

from benchmark import metrics, report
from fieldcheck.cases import CaseLoadError, discover_cases, load_case

CAPABILITY = "lip_sync"
PROVIDER_ID = "syncnet-s3fd-http"  # same provider_id the production HTTP adapter uses
MODEL_ID = "syncnet-v2"
_S3FD_RELATIVE = Path("lipsync/sfd_face.pth")
_SYNCNET_RELATIVE = Path("lipsync/syncnet_v2.model")

_DATASET = {
    "dataset_id": "fieldcheck-local-cases",
    "name": "Real selfie-video evidence dropped locally under fieldcheck/local_cases/",
    "version": "n/a",
    "split_policy": "developer_local_real_samples",
    "sensitivity": "real_pii",
    "notes": (
        "Developer's own consented data, not a governed dataset - not "
        "registered in benchmark/datasets/registry.json."
    ),
}


class _Predictor(Protocol):
    def predict_video_bytes(self, video_bytes: bytes, *, suffix: str) -> Any: ...


def _skipped_report(reason: str) -> dict[str, Any]:
    return report.build_report(
        capability=CAPABILITY,
        provider_id=PROVIDER_ID,
        model_id=MODEL_ID,
        dataset=_DATASET,
        sample_count=0,
        excluded_count=0,
        metrics_out={},
        latency_ms=[],
        skipped_models=[{"model_id": MODEL_ID, "reason": reason}],
        notes=(
            "Prerequisite missing - see skipped_models. Never falls back to the HTTP/Docker "
            "lip-sync service; this runner always evaluates SyncNet locally, in-process."
        ),
    )


def run(
    model_dir: Path, cases_root: Path, *, predictor: _Predictor | None = None
) -> dict[str, Any]:
    """Evaluate SyncNet locally, in-process (no Docker/HTTP), against real
    selfie-video evidence under `cases_root` (normally fieldcheck's
    local_cases/). Never fabricates video - if no usable case exists this
    returns a sample_count=0 scaffold report rather than raising."""
    case_dirs = discover_cases(cases_root) if cases_root.is_dir() else []

    if predictor is None:
        s3fd_path = model_dir / _S3FD_RELATIVE
        syncnet_path = model_dir / _SYNCNET_RELATIVE
        if not s3fd_path.is_file() or not syncnet_path.is_file():
            return _skipped_report(
                f"SyncNet weights not found locally at {s3fd_path} / {syncnet_path}; run "
                "'python scripts/models.py --include syncnet-v2,s3fd-face' first"
            )
        try:
            import syncnet_python  # noqa: F401
        except ImportError:
            return _skipped_report(
                "syncnet-python package not installed - it's a benchmark_only dev "
                "dependency, run 'uv sync --group dev' first"
            )

        from ai_modules.lipsync.app.predictor import SyncNetPredictor, SyncNetSettings

        settings = SyncNetSettings(
            s3fd_weights=s3fd_path, syncnet_weights=syncnet_path, device="cpu"
        )
        predictor = SyncNetPredictor(settings)

    latencies: list[float] = []
    verdict_counts: dict[str, int] = {}
    confidences: list[float] = []
    excluded = 0
    skipped_cases: list[dict[str, Any]] = []

    for case_dir in case_dirs:
        try:
            case = load_case(case_dir)
        except CaseLoadError:
            excluded += 1
            continue
        if not case.has_video:
            skipped_cases.append({"case_id": case.case_id, "reason": "no selfie_video"})
            continue

        video = next(item for item in case.evidence if item.evidence_type == "SELFIE_VIDEO")
        start = perf_counter()
        result = predictor.predict_video_bytes(video.payload, suffix=".mp4")
        latencies.append((perf_counter() - start) * 1000)
        verdict_counts[result.verdict] = verdict_counts.get(result.verdict, 0) + 1
        confidences.append(result.confidence)

    sample_count = sum(verdict_counts.values())
    metrics_out = {
        "verdict_counts": verdict_counts,
        "confidence_mean": metrics.mean(confidences),
        "confidence_p50": metrics.percentile(confidences, 0.5),
        "cases_evaluated": sample_count,
        "cases_skipped": len(skipped_cases),
        "skipped_cases": skipped_cases,
    }

    notes = (
        "Runs SyncNet locally in-process (ai_modules/lipsync/app/predictor.py's "
        "SyncNetPredictor, imported directly - no Docker/HTTP microservice involved) "
        "against real selfie-video evidence dropped under fieldcheck/local_cases/ - not "
        "a licensed/distributable dataset, so it is not registered in "
        "benchmark/datasets/registry.json (see fieldcheck/README.md). "
    )
    notes += (
        f"{sample_count} case(s) evaluated."
        if sample_count
        else (
            "0 samples: this ran as an empty scaffold. Drop a case with a selfie_video "
            "under fieldcheck/local_cases/ to populate it."
        )
    )

    return report.build_report(
        capability=CAPABILITY,
        provider_id=PROVIDER_ID,
        model_id=MODEL_ID,
        dataset=_DATASET,
        sample_count=sample_count,
        excluded_count=excluded,
        metrics_out=metrics_out,
        latency_ms=latencies,
        skipped_models=[],
        notes=notes,
    )
