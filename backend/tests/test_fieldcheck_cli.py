from __future__ import annotations

import json
from pathlib import Path

import pytest
from support.fake_registry import build_fake_registry
from support.tiny_media import tiny_jpeg_bytes, tiny_mp4_bytes

from app.adapters.analyzer import OfflineModelAnalyzer
from fieldcheck import cli
from fieldcheck.paths import REPO_ROOT


def _patch_analyzer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    registry = build_fake_registry(tmp_path / "manifest")
    analyzer = OfflineModelAnalyzer(registry, require_models=False, profile="technical_demo")
    monkeypatch.setattr(cli, "build_analyzer", lambda settings: analyzer)


def _write_case(case_dir: Path, *, with_video: bool = True) -> None:
    case_dir.mkdir(parents=True)
    (case_dir / "document_front.jpg").write_bytes(tiny_jpeg_bytes())
    (case_dir / "document_back.jpg").write_bytes(tiny_jpeg_bytes())
    if with_video:
        (case_dir / "selfie_video.mp4").write_bytes(tiny_mp4_bytes())
        (case_dir / "case.json").write_text(json.dumps({"voice_challenge": "1 2 3"}))


def test_adhoc_writes_result_and_exits_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _patch_analyzer(monkeypatch, tmp_path)
    case_dir = tmp_path / "cases" / "my-case"
    _write_case(case_dir)
    out_path = tmp_path / "out" / "result.json"

    exit_code = cli.main(["adhoc", "--case", str(case_dir), "--out", str(out_path)])

    assert exit_code == 0
    written = json.loads(out_path.read_text())
    assert written["contract_version"] == "ekyc-analysis/1.0"
    captured = capsys.readouterr()
    assert "my-case" in captured.out


def test_adhoc_document_only_case_uses_analyze_document(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_analyzer(monkeypatch, tmp_path)
    case_dir = tmp_path / "cases" / "doc-only"
    _write_case(case_dir, with_video=False)
    out_path = tmp_path / "out" / "result.json"

    exit_code = cli.main(["adhoc", "--case", str(case_dir), "--out", str(out_path)])

    assert exit_code == 0
    written = json.loads(out_path.read_text())
    assert written["schema_version"] == "demo-ocr-rerun/1.0"


def test_adhoc_missing_case_dir_returns_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_analyzer(monkeypatch, tmp_path)

    exit_code = cli.main(["adhoc", "--case", str(tmp_path / "does-not-exist")])

    assert exit_code == 1


def test_adhoc_refuses_unsafe_out_path_inside_repo(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_analyzer(monkeypatch, tmp_path)
    case_dir = tmp_path / "cases" / "my-case"
    _write_case(case_dir)
    unsafe_path = REPO_ROOT / "fieldcheck-test-unsafe-output.json"
    try:
        with pytest.raises(SystemExit) as exc_info:
            cli.main(["adhoc", "--case", str(case_dir), "--out", str(unsafe_path)])
        assert exc_info.value.code == 2
        assert not unsafe_path.exists()
    finally:
        unsafe_path.unlink(missing_ok=True)


def test_batch_runs_every_case_and_writes_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_analyzer(monkeypatch, tmp_path)
    cases_root = tmp_path / "cases"
    _write_case(cases_root / "case-1")
    _write_case(cases_root / "case-2", with_video=False)
    out_dir = tmp_path / "out"

    exit_code = cli.main(
        ["batch", "--cases-root", str(cases_root), "--out-dir", str(out_dir), "--save-per-case"]
    )

    assert exit_code == 0
    summary = json.loads((out_dir / "summary.json").read_text())
    assert summary["case_count"] == 2
    assert summary["status_counts"] == {"RAN": 2}
    assert (out_dir / "cases" / "case-1.json").exists()
    assert (out_dir / "cases" / "case-2.json").exists()


def test_batch_no_cases_found_returns_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_analyzer(monkeypatch, tmp_path)
    empty_root = tmp_path / "empty"
    empty_root.mkdir()

    exit_code = cli.main(
        ["batch", "--cases-root", str(empty_root), "--out-dir", str(tmp_path / "out")]
    )

    assert exit_code == 1
