from __future__ import annotations

import json
from pathlib import Path

import pytest
from support.tiny_media import tiny_jpeg_bytes, tiny_mp4_bytes

from fieldcheck.cases import CaseLoadError, discover_cases, load_case


def test_load_case_detects_cccd_front_back(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-a"
    case_dir.mkdir()
    (case_dir / "document_front.jpg").write_bytes(tiny_jpeg_bytes())
    (case_dir / "document_back.jpg").write_bytes(tiny_jpeg_bytes())

    case = load_case(case_dir)

    assert case.case_id == "case-a"
    assert case.document_type == "CCCD"
    assert not case.has_video
    assert {item.evidence_type for item in case.evidence} == {"DOCUMENT_FRONT", "DOCUMENT_BACK"}
    assert case.voice_challenge == ""
    assert case.expected == {}


def test_load_case_detects_passport(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-b"
    case_dir.mkdir()
    (case_dir / "passport_page.png").write_bytes(tiny_jpeg_bytes())

    case = load_case(case_dir)

    assert case.document_type == "PASSPORT_TD3"


def test_load_case_with_video_and_sidecar(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-c"
    case_dir.mkdir()
    (case_dir / "document_front.jpg").write_bytes(tiny_jpeg_bytes())
    (case_dir / "document_back.jpg").write_bytes(tiny_jpeg_bytes())
    (case_dir / "selfie_video.mp4").write_bytes(tiny_mp4_bytes())
    (case_dir / "case.json").write_text(
        json.dumps({"voice_challenge": "1 2 3", "expected": {"face_match": "SCORE_AVAILABLE"}})
    )

    case = load_case(case_dir)

    assert case.has_video
    assert case.voice_challenge == "1 2 3"
    assert case.expected == {"face_match": "SCORE_AVAILABLE"}


def test_load_case_document_type_override_resolves_ambiguity(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-d"
    case_dir.mkdir()
    (case_dir / "document_front.jpg").write_bytes(tiny_jpeg_bytes())
    (case_dir / "passport_page.jpg").write_bytes(tiny_jpeg_bytes())
    (case_dir / "case.json").write_text(json.dumps({"document_type": "CCCD"}))

    case = load_case(case_dir)

    assert case.document_type == "CCCD"


def test_load_case_ambiguous_document_type_without_override_raises(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-e"
    case_dir.mkdir()
    (case_dir / "document_front.jpg").write_bytes(tiny_jpeg_bytes())
    (case_dir / "passport_page.jpg").write_bytes(tiny_jpeg_bytes())

    with pytest.raises(CaseLoadError, match="ambiguous"):
        load_case(case_dir)


def test_load_case_no_document_evidence_raises(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-f"
    case_dir.mkdir()
    (case_dir / "selfie_video.mp4").write_bytes(tiny_mp4_bytes())

    with pytest.raises(CaseLoadError, match="no document evidence"):
        load_case(case_dir)


def test_load_case_no_recognized_files_raises(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-g"
    case_dir.mkdir()
    (case_dir / "readme.txt").write_text("not evidence")

    with pytest.raises(CaseLoadError, match="no recognized evidence"):
        load_case(case_dir)


def test_load_case_rejects_disallowed_suffix_for_evidence_type(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-h"
    case_dir.mkdir()
    (case_dir / "document_front.mp4").write_bytes(tiny_mp4_bytes())

    with pytest.raises(CaseLoadError, match="not an allowed content type"):
        load_case(case_dir)


def test_load_case_rejects_duplicate_stem_match(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-i"
    case_dir.mkdir()
    (case_dir / "document_front.jpg").write_bytes(tiny_jpeg_bytes())
    (case_dir / "document_front.png").write_bytes(tiny_jpeg_bytes())

    with pytest.raises(CaseLoadError, match="multiple files match"):
        load_case(case_dir)


def test_load_case_rejects_non_directory(tmp_path: Path) -> None:
    not_a_dir = tmp_path / "not-a-dir.txt"
    not_a_dir.write_text("x")

    with pytest.raises(CaseLoadError, match="not a directory"):
        load_case(not_a_dir)


def test_load_case_rejects_invalid_json_sidecar(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-j"
    case_dir.mkdir()
    (case_dir / "document_front.jpg").write_bytes(tiny_jpeg_bytes())
    (case_dir / "document_back.jpg").write_bytes(tiny_jpeg_bytes())
    (case_dir / "case.json").write_text("{not json")

    with pytest.raises(CaseLoadError, match="invalid JSON"):
        load_case(case_dir)


def test_load_case_rejects_non_object_expected(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-k"
    case_dir.mkdir()
    (case_dir / "document_front.jpg").write_bytes(tiny_jpeg_bytes())
    (case_dir / "document_back.jpg").write_bytes(tiny_jpeg_bytes())
    (case_dir / "case.json").write_text(json.dumps({"expected": ["not", "a", "dict"]}))

    with pytest.raises(CaseLoadError, match='"expected" must be an object'):
        load_case(case_dir)


def test_discover_cases_sorts_and_filters(tmp_path: Path) -> None:
    for name in ("beta", "alpha", "other"):
        (tmp_path / name).mkdir()
    (tmp_path / "not-a-dir.txt").write_text("x")

    assert [p.name for p in discover_cases(tmp_path)] == ["alpha", "beta", "other"]
    assert [p.name for p in discover_cases(tmp_path, pattern="a*")] == ["alpha"]


def test_discover_cases_rejects_non_directory_root(tmp_path: Path) -> None:
    not_a_dir = tmp_path / "file.txt"
    not_a_dir.write_text("x")

    with pytest.raises(CaseLoadError, match="not a directory"):
        discover_cases(not_a_dir)
