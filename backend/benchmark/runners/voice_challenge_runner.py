from __future__ import annotations

import tempfile
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol

from ai_modules.ekyc.voice_challenge import VoiceVerifier
from benchmark import metrics, report
from fieldcheck.cases import CaseLoadError, discover_cases, load_case

CAPABILITY = "voice_challenge"
PROVIDER_ID = "vosk-small-vn-0.4"

_DATASET = {
    "dataset_id": "fieldcheck-local-cases",
    "name": "Real selfie-video evidence dropped locally under fieldcheck/local_cases/",
    "version": "n/a",
    "split_policy": "developer_local_real_samples",
    "sensitivity": "real_pii",
    "approval_status": "developer_own_consented_data_not_a_governed_dataset",
}


class _Verifier(Protocol):
    def verify(self, media_path: Path, challenge: str) -> dict[str, Any]: ...


def run(
    model_dir: Path, cases_root: Path, *, verifier: _Verifier | None = None
) -> dict[str, Any]:
    """Evaluate the real vosk-small-vn-0.4 voice-challenge model against real
    selfie-video evidence under `cases_root` (normally fieldcheck's
    local_cases/). Never fabricates audio - if no usable case exists this
    returns a sample_count=0 scaffold report rather than raising, per
    docs/IMPLEMENTATION_STATUS.md's stated principle for this capability."""
    case_dirs = discover_cases(cases_root) if cases_root.is_dir() else []

    latencies: list[float] = []
    similarities: list[float] = []
    ok_count = 0
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
        if not case.voice_challenge:
            skipped_cases.append(
                {"case_id": case.case_id, "reason": "no voice_challenge in case.json"}
            )
            continue

        if verifier is None:
            verifier = VoiceVerifier(model_dir, device="cpu")

        video = next(item for item in case.evidence if item.evidence_type == "SELFIE_VIDEO")
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as stream:
            stream.write(video.payload)
            media_path = Path(stream.name)
        try:
            start = perf_counter()
            result = verifier.verify(media_path, case.voice_challenge)
            latencies.append((perf_counter() - start) * 1000)
        finally:
            media_path.unlink(missing_ok=True)

        similarities.append(result["similarity"])
        if result["status"] == "OK":
            ok_count += 1

    sample_count = len(similarities)
    metrics_out = {
        "similarity_mean": metrics.mean(similarities),
        "similarity_p50": metrics.percentile(similarities, 0.5),
        "ok_rate": ok_count / sample_count if sample_count else None,
        "cases_evaluated": sample_count,
        "cases_skipped": len(skipped_cases),
        "skipped_cases": skipped_cases,
    }

    notes = (
        "Evaluates the real vosk-small-vn-0.4 voice-challenge model against real "
        "selfie-video evidence dropped under fieldcheck/local_cases/ - not a licensed/"
        "distributable dataset, so it is not registered in benchmark/datasets/registry.json "
        "(see fieldcheck/README.md). "
    )
    notes += (
        f"{sample_count} case(s) evaluated."
        if sample_count
        else (
            "0 samples: this ran as an empty scaffold. Drop a case with a selfie_video "
            "and a matching voice_challenge in case.json under fieldcheck/local_cases/ "
            "to populate it."
        )
    )

    return report.build_report(
        capability=CAPABILITY,
        provider_id=PROVIDER_ID,
        model_id=PROVIDER_ID,
        dataset=_DATASET,
        sample_count=sample_count,
        excluded_count=excluded,
        metrics_out=metrics_out,
        latency_ms=latencies,
        skipped_models=[],
        notes=notes,
    )
