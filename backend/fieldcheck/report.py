from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fieldcheck.paths import DEFAULT_LOCAL_RUNS_DIR, REPO_ROOT


def _check_repo_boundary(resolved: Path, *, force: bool) -> None:
    """Real evidence and everything derived from it must never land in git.
    Refuse (exit 2) any output path inside the repo that isn't the designated
    gitignored local_runs dir, unless the caller explicitly forces it."""
    inside_repo = resolved.is_relative_to(REPO_ROOT)
    inside_local_runs = resolved.is_relative_to(DEFAULT_LOCAL_RUNS_DIR.resolve())
    if inside_repo and not inside_local_runs and not force:
        print(
            f"refusing to write to {resolved} - it is inside the git repository and is not "
            f"the gitignored {DEFAULT_LOCAL_RUNS_DIR} directory; real evidence-derived data "
            "must never be committed. Pass --force to override.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def resolve_output_path(path: Path | None, *, stem: str, force: bool = False) -> Path:
    if path is None:
        DEFAULT_LOCAL_RUNS_DIR.mkdir(parents=True, exist_ok=True)
        return DEFAULT_LOCAL_RUNS_DIR / f"{stem}-{_timestamp()}.json"
    resolved = Path(path).resolve()
    _check_repo_boundary(resolved, force=force)
    return resolved


def resolve_output_dir(path: Path | None, *, force: bool = False) -> Path:
    if path is None:
        out_dir = DEFAULT_LOCAL_RUNS_DIR / _timestamp()
    else:
        out_dir = Path(path).resolve()
        _check_repo_boundary(out_dir, force=force)
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def write_json(data: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n"
    path.write_text(payload, encoding="utf-8")
    return path
