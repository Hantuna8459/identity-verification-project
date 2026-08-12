from __future__ import annotations

from pathlib import Path

from support.fake_registry import build_fake_registry
from support.tiny_media import tiny_jpeg_bytes, tiny_mp4_bytes

from app.adapters.analyzer import OfflineModelAnalyzer
from app.domain.ports import EvidencePayload
from fieldcheck.cases import Case
from fieldcheck.runner import run_case, run_case_dir


def _analyzer(tmp_path: Path) -> OfflineModelAnalyzer:
    registry = build_fake_registry(tmp_path)
    return OfflineModelAnalyzer(registry, require_models=False, profile="technical_demo")


def test_run_case_document_only_uses_analyze_document(tmp_path: Path) -> None:
    analyzer = _analyzer(tmp_path)
    case = Case(
        case_id="doc-only",
        source_dir=tmp_path,
        evidence=[
            # document_ocr is faked - it never decodes these bytes, so
            # arbitrary content is fine for the document-only (no video) path.
            EvidencePayload("DOCUMENT_FRONT", "image/jpeg", b"arbitrary-bytes-ocr-is-faked"),
            EvidencePayload("DOCUMENT_BACK", "image/jpeg", b"arbitrary-bytes-ocr-is-faked"),
        ],
        document_type="CCCD",
        voice_challenge="",
    )

    result = run_case(analyzer, case)

    assert result.status == "RAN"
    assert result.mode == "analyze_document"
    assert result.result is not None
    assert result.result["schema_version"] == "demo-ocr-rerun/1.0"
    assert set(result.result["documents"]) == {"document_front", "document_back"}
    documents = result.result["documents"].values()
    assert all(doc["execution_status"] == "COMPLETED" for doc in documents)


def test_run_case_full_pipeline_with_video(tmp_path: Path) -> None:
    analyzer = _analyzer(tmp_path)
    case = Case(
        case_id="full",
        source_dir=tmp_path,
        evidence=[
            # decode_image()/video_frames() run for real even with faked
            # capability providers, so these must be genuinely decodable.
            EvidencePayload("DOCUMENT_FRONT", "image/jpeg", tiny_jpeg_bytes()),
            EvidencePayload("DOCUMENT_BACK", "image/jpeg", tiny_jpeg_bytes()),
            EvidencePayload("SELFIE_VIDEO", "video/mp4", tiny_mp4_bytes()),
        ],
        document_type="CCCD",
        voice_challenge="1 2 3 4 5 6",
    )

    result = run_case(analyzer, case)

    assert result.status == "RAN"
    assert result.mode == "analyze"
    assert result.result is not None
    body = result.result
    assert body["contract_version"] == "ekyc-analysis/1.0"
    assert body["execution_status"] == "COMPLETED"
    capabilities = body["capabilities"]
    assert capabilities["face_match"]["execution_status"] == "COMPLETED"
    assert capabilities["face_match"]["metrics"]["cosine_similarity"] == 0.8
    assert capabilities["ocr"]["documents"]["document_front"]["execution_status"] == "COMPLETED"


def test_run_case_catches_run_failure(tmp_path: Path) -> None:
    """CCCD needs both DOCUMENT_FRONT and DOCUMENT_BACK for the full pipeline
    - EkycOrchestrator.analyze() does an unguarded by_type["DOCUMENT_BACK"]
    lookup outside any try/except. A case with only front + video is
    loadable but not runnable; run_case must catch that, not crash the
    caller (a batch run in particular)."""
    analyzer = _analyzer(tmp_path)
    case = Case(
        case_id="missing-back",
        source_dir=tmp_path,
        evidence=[
            EvidencePayload("DOCUMENT_FRONT", "image/jpeg", tiny_jpeg_bytes()),
            EvidencePayload("SELFIE_VIDEO", "video/mp4", tiny_mp4_bytes()),
        ],
        document_type="CCCD",
        voice_challenge="",
    )

    result = run_case(analyzer, case)

    assert result.status == "RUN_FAILED"
    assert result.error is not None
    assert "DOCUMENT_BACK" in result.error
    assert result.result is None


def test_run_case_dir_catches_load_failure(tmp_path: Path) -> None:
    analyzer = _analyzer(tmp_path)
    empty_dir = tmp_path / "empty-case"
    empty_dir.mkdir()

    result = run_case_dir(analyzer, empty_dir)

    assert result.status == "LOAD_FAILED"
    assert result.case_id == "empty-case"
    assert result.result is None


def test_run_case_dir_loads_and_runs(tmp_path: Path) -> None:
    analyzer = _analyzer(tmp_path)
    case_dir = tmp_path / "case-1"
    case_dir.mkdir()
    (case_dir / "document_front.jpg").write_bytes(tiny_jpeg_bytes())
    (case_dir / "document_back.jpg").write_bytes(tiny_jpeg_bytes())

    result = run_case_dir(analyzer, case_dir)

    assert result.status == "RAN"
    assert result.case_id == "case-1"
