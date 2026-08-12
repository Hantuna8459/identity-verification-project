from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path

from app.api import ALLOWED_CONTENT_TYPES
from app.domain.ports import EvidencePayload


class CaseLoadError(ValueError):
    """A case directory is missing required evidence, or its layout is ambiguous."""


# Filename stem (case-insensitive) -> evidence_type understood by the real
# pipeline (app.api.ALLOWED_CONTENT_TYPES is the source of truth for which
# content types are legal per evidence_type).
_EVIDENCE_STEMS: dict[str, str] = {
    "document_front": "DOCUMENT_FRONT",
    "document_back": "DOCUMENT_BACK",
    "passport_page": "PASSPORT_PAGE",
    "selfie_video": "SELFIE_VIDEO",
}

_SUFFIX_CONTENT_TYPE: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
}


@dataclass(frozen=True)
class Case:
    case_id: str
    source_dir: Path
    evidence: list[EvidencePayload]
    document_type: str
    voice_challenge: str
    expected: dict[str, str] = field(default_factory=dict)

    @property
    def has_video(self) -> bool:
        return any(item.evidence_type == "SELFIE_VIDEO" for item in self.evidence)


def _find_evidence_files(case_dir: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for entry in sorted(case_dir.iterdir()):
        if not entry.is_file():
            continue
        evidence_type = _EVIDENCE_STEMS.get(entry.stem.lower())
        if evidence_type is None:
            continue
        if evidence_type in found:
            raise CaseLoadError(
                f"{case_dir}: multiple files match evidence type {evidence_type} "
                f"({found[evidence_type].name!r} and {entry.name!r})"
            )
        found[evidence_type] = entry
    return found


def _load_payload(evidence_type: str, path: Path) -> EvidencePayload:
    content_type = _SUFFIX_CONTENT_TYPE.get(path.suffix.lower())
    allowed = ALLOWED_CONTENT_TYPES.get(evidence_type, set())
    if content_type is None or content_type not in allowed:
        raise CaseLoadError(
            f"{path}: suffix {path.suffix!r} is not an allowed content type for "
            f"{evidence_type} (allowed: {sorted(allowed)})"
        )
    return EvidencePayload(
        evidence_type=evidence_type, content_type=content_type, payload=path.read_bytes()
    )


def _detect_document_type(found: dict[str, Path]) -> str:
    has_passport = "PASSPORT_PAGE" in found
    has_front_back = "DOCUMENT_FRONT" in found or "DOCUMENT_BACK" in found
    if has_passport and has_front_back:
        raise CaseLoadError(
            "case has both passport_page and document_front/back files - ambiguous "
            'document_type, set "document_type" explicitly in case.json'
        )
    if has_passport:
        return "PASSPORT_TD3"
    if has_front_back:
        return "CCCD"
    raise CaseLoadError("case has no document evidence (document_front/back or passport_page)")


def _load_sidecar(case_dir: Path) -> dict:
    sidecar = case_dir / "case.json"
    if not sidecar.is_file():
        return {}
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CaseLoadError(f"{sidecar}: invalid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise CaseLoadError(f"{sidecar}: must be a JSON object")
    return data


def load_case(case_dir: Path) -> Case:
    """Load one evidence case from a directory.

    Layout: files named document_front/document_back/passport_page/selfie_video
    (any recognized image/video suffix), plus an optional case.json sidecar
    carrying document_type/voice_challenge/expected overrides. See
    backend/fieldcheck/README.md for the full schema.
    """
    case_dir = Path(case_dir)
    if not case_dir.is_dir():
        raise CaseLoadError(f"{case_dir}: not a directory")

    found = _find_evidence_files(case_dir)
    if not found:
        raise CaseLoadError(f"{case_dir}: no recognized evidence files found")

    sidecar = _load_sidecar(case_dir)
    document_type = sidecar.get("document_type") or _detect_document_type(found)
    voice_challenge = sidecar.get("voice_challenge", "")
    expected = sidecar.get("expected", {})
    if not isinstance(expected, dict):
        raise CaseLoadError(f'{case_dir}/case.json: "expected" must be an object')

    evidence = [_load_payload(evidence_type, path) for evidence_type, path in found.items()]
    return Case(
        case_id=case_dir.name,
        source_dir=case_dir,
        evidence=evidence,
        document_type=document_type,
        voice_challenge=voice_challenge,
        expected=expected,
    )


def discover_cases(root: Path, pattern: str = "*") -> list[Path]:
    """Every immediate subdirectory of `root` whose name matches `pattern`,
    sorted by name. Does not check evidence presence - `load_case()` raises
    per-case if a discovered directory turns out to have none."""
    root = Path(root)
    if not root.is_dir():
        raise CaseLoadError(f"{root}: not a directory")
    return sorted(
        entry for entry in root.iterdir() if entry.is_dir() and fnmatch.fnmatch(entry.name, pattern)
    )
