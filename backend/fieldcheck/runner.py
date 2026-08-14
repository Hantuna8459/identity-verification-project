from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.adapters.analyzer import OfflineModelAnalyzer
from app.adapters.ekyc_providers import build_capability_registry
from app.core.config import Settings
from fieldcheck.cases import Case, CaseLoadError, load_case


def build_analyzer(settings: Settings) -> OfflineModelAnalyzer:
    """Production composition path - builds a real CapabilityRegistry from
    Settings.model_dir/model_profile/provider_* chains (same composition root
    the live API uses, app.adapters.ekyc_providers.build_capability_registry)
    and wraps it in OfflineModelAnalyzer. Never used by tests - see
    tests/support for the fakes-backed equivalent."""
    registry = build_capability_registry(settings)
    return OfflineModelAnalyzer(
        registry,
        require_models=False,
        profile=settings.model_profile,
        max_video_frames=settings.max_video_frames,
        max_face_match_frames=settings.max_face_match_frames,
        replay_suspicious_threshold=settings.replay_suspicious_threshold,
        camera_injection_suspicious_threshold=settings.camera_injection_suspicious_threshold,
        face_match_threshold=settings.face_match_threshold,
        face_match_consider_threshold=settings.face_match_consider_threshold,
        passive_liveness_threshold=settings.passive_liveness_threshold,
        passive_liveness_consider_threshold=settings.passive_liveness_consider_threshold,
        visual_deepfake_threshold=settings.visual_deepfake_threshold,
        face_quality_min_video_face_frames=settings.face_quality_min_video_face_frames,
        face_quality_blur_threshold=settings.face_quality_blur_threshold,
        face_quality_min_coverage=settings.face_quality_min_coverage,
        face_quality_max_coverage=settings.face_quality_max_coverage,
        face_quality_yaw_threshold=settings.face_quality_yaw_threshold,
        face_quality_roll_threshold=settings.face_quality_roll_threshold,
    )


@dataclass(frozen=True)
class CaseRunResult:
    case_id: str
    status: str  # "RAN" | "LOAD_FAILED" | "RUN_FAILED"
    mode: str | None = None  # "analyze" | "analyze_document", only set when status == "RAN"
    result: dict[str, Any] | None = None
    expected: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    duration_ms: float | None = None


def run_case(analyzer: OfflineModelAnalyzer, case: Case) -> CaseRunResult:
    """Run one already-loaded case through the analyzer. Pure function (no
    filesystem access) so tests can call it directly against a fakes-backed
    analyzer without touching load_case()/the filesystem at all."""
    started = time.perf_counter()
    try:
        if case.has_video:
            result = analyzer.analyze(
                uuid.uuid4(), case.document_type, case.voice_challenge, case.evidence
            )
            mode = "analyze"
        else:
            result = analyzer.analyze_document(case.document_type, case.evidence)
            mode = "analyze_document"
    except Exception as exc:  # a single bad case must not abort a batch run
        duration_ms = (time.perf_counter() - started) * 1000
        return CaseRunResult(
            case_id=case.case_id,
            status="RUN_FAILED",
            expected=case.expected,
            error=f"{type(exc).__name__}: {exc}",
            duration_ms=duration_ms,
        )
    duration_ms = (time.perf_counter() - started) * 1000
    return CaseRunResult(
        case_id=case.case_id,
        status="RAN",
        mode=mode,
        result=result,
        expected=case.expected,
        duration_ms=duration_ms,
    )


def run_case_dir(analyzer: OfflineModelAnalyzer, case_dir: Path) -> CaseRunResult:
    """Load + run a case directory in one step; catches CaseLoadError instead
    of raising, so a batch run can keep going past one malformed case dir."""
    case_dir = Path(case_dir)
    try:
        case = load_case(case_dir)
    except CaseLoadError as exc:
        return CaseRunResult(case_id=case_dir.name, status="LOAD_FAILED", error=str(exc))
    return run_case(analyzer, case)
