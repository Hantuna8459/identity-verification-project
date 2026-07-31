#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any

CHUNK_SIZE = 1024 * 1024
ALLOWED_APPROVAL_STATUSES = {
    "quarantined",
    "evaluation_only",
    "production_approved",
    "rejected",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            value.update(chunk)
    return value.hexdigest()


def validate(path: Path, artifact: dict[str, Any]) -> str | None:
    if not path.is_file():
        return "missing"
    expected_size = int(artifact["size_bytes"])
    if path.stat().st_size != expected_size:
        return f"size mismatch ({path.stat().st_size} != {expected_size})"
    actual = digest(path)
    if actual != artifact["sha256"]:
        return f"sha256 mismatch ({actual})"
    return None


def download_url(url: str, destination: Path, retries: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        temporary: Path | None = None
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "vid-ekyc-models/1.1"})
            with urllib.request.urlopen(request, timeout=300) as response:
                with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
                    temporary = Path(output.name)
                    while chunk := response.read(CHUNK_SIZE):
                        output.write(chunk)
            temporary.replace(destination)
            destination.chmod(0o644)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            if attempt < retries:
                time.sleep(min(2**attempt, 15))
    raise RuntimeError(f"Failed downloading {url}: {last_error}")


def _safe_member(member: str) -> str:
    path = PurePosixPath(member)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise RuntimeError(f"Unsafe archive member: {member!r}")
    return path.as_posix()


def extract_archive(
    archive_path: Path,
    members: Iterable[dict[str, Any]],
    models_dir: Path,
) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        for artifact in members:
            source_path = _safe_member(str(artifact["source_path"]))
            if source_path not in names:
                raise RuntimeError(f"Archive member missing: {source_path}")
            destination = models_dir / str(artifact["path"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary: Path | None = None
            try:
                with archive.open(source_path) as source:
                    with tempfile.NamedTemporaryFile(
                        dir=destination.parent,
                        delete=False,
                    ) as output:
                        temporary = Path(output.name)
                        shutil.copyfileobj(source, output, CHUNK_SIZE)
                issue = validate(temporary, artifact)
                if issue:
                    raise RuntimeError(f"{artifact['path']}: {issue}")
                temporary.replace(destination)
                destination.chmod(0o644)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)


def _entry_artifacts(entry: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = entry.get("artifacts")
    if isinstance(artifacts, list):
        return artifacts
    return [entry]


def _entry_enabled(entry: dict[str, Any], profile: str) -> bool:
    status = str(entry.get("approval_status", "quarantined"))
    if status not in ALLOWED_APPROVAL_STATUSES:
        raise RuntimeError(f"{entry.get('id', 'unknown')}: invalid approval_status {status!r}")
    if status in {"quarantined", "rejected"}:
        return False
    scopes = entry.get("usage_scope", [])
    return profile in scopes or "all" in scopes


def _copy_local_artifact(
    source: Path,
    destination: Path,
    artifact: dict[str, Any],
) -> str | None:
    if not source.is_file():
        return f"local artifact missing: {source}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copyfile(source, destination)
        destination.chmod(0o644)
    return validate(destination, artifact)


def _process_archive(
    entry: dict[str, Any],
    models_dir: Path,
    cache_dir: Path,
    retries: int,
    verify_only: bool,
) -> list[str]:
    failures: list[str] = []
    artifacts = _entry_artifacts(entry)
    issues = [
        f"{artifact['path']}: {issue}"
        for artifact in artifacts
        if (issue := validate(models_dir / str(artifact["path"]), artifact))
    ]
    if not issues:
        for artifact in artifacts:
            destination = models_dir / str(artifact["path"])
            print(f"OK    {entry['id']}:{artifact['path']} ({destination.stat().st_size} bytes)")
        return failures
    if verify_only:
        return [f"{entry['id']}:{issue}" for issue in issues]

    archive = entry["archive"]
    cache_path = cache_dir / str(archive["filename"])
    archive_issue = validate(cache_path, archive)
    if archive_issue:
        print(f"FETCH {entry['id']}: archive {archive_issue}")
        try:
            download_url(str(archive["url"]), cache_path, retries)
        except RuntimeError as exc:
            return [str(exc)]
        archive_issue = validate(cache_path, archive)
    if archive_issue:
        return [f"{entry['id']}: archive {archive_issue}"]
    try:
        extract_archive(cache_path, artifacts, models_dir)
    except (RuntimeError, zipfile.BadZipFile) as exc:
        return [f"{entry['id']}: {exc}"]
    for artifact in artifacts:
        destination = models_dir / str(artifact["path"])
        issue = validate(destination, artifact)
        if issue:
            failures.append(f"{entry['id']}:{artifact['path']}: {issue}")
        else:
            print(f"OK    {entry['id']}:{artifact['path']} ({destination.stat().st_size} bytes)")
    return failures


def _process_direct(
    entry: dict[str, Any],
    models_dir: Path,
    retries: int,
    verify_only: bool,
    artifact_sources: dict[str, Path],
) -> list[str]:
    failures: list[str] = []
    artifacts = _entry_artifacts(entry)
    for artifact in artifacts:
        destination = models_dir / str(artifact["path"])
        issue = validate(destination, artifact)
        if issue and entry["id"] in artifact_sources and len(artifacts) == 1:
            issue = _copy_local_artifact(artifact_sources[entry["id"]], destination, artifact)
        if issue and not verify_only:
            url = artifact.get("url") or entry.get("url")
            if not url:
                failures.append(
                    f"{entry['id']} has no public URL; provide the pinned project artifact at "
                    f"{destination}"
                )
                continue
            print(f"FETCH {entry['id']}:{artifact['path']}: {issue}")
            try:
                download_url(str(url), destination, retries)
            except RuntimeError as exc:
                failures.append(str(exc))
                continue
            issue = validate(destination, artifact)
        if issue:
            failures.append(f"{entry['id']}:{artifact['path']}: {issue}")
        else:
            print(f"OK    {entry['id']}:{artifact['path']} ({destination.stat().st_size} bytes)")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and verify pinned V-ID eKYC models")
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--manifest", type=Path, default=Path("models/manifest.json"))
    parser.add_argument("--profile", default="technical_demo")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Only process the given enabled model id; may be repeated",
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        metavar="MODEL_ID=PATH",
        help="Provide a local artifact for a single-file model without a download URL",
    )
    args = parser.parse_args()

    artifact_sources: dict[str, Path] = {}
    for value in args.artifact:
        model_id, separator, raw_path = value.partition("=")
        if not separator or not model_id or not raw_path:
            parser.error(f"Invalid --artifact value: {value!r}; expected MODEL_ID=PATH")
        artifact_sources[model_id] = Path(raw_path)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    cache_dir = args.cache_dir or args.models_dir / ".cache" / "downloads"
    selected = set(args.include)
    failures: list[str] = []
    seen: set[str] = set()
    for entry in manifest.get("models", []):
        model_id = str(entry["id"])
        if model_id in seen:
            failures.append(f"duplicate model id: {model_id}")
            continue
        seen.add(model_id)
        if selected and model_id not in selected:
            continue
        try:
            enabled = _entry_enabled(entry, args.profile)
        except RuntimeError as exc:
            failures.append(str(exc))
            continue
        if not enabled:
            print(f"SKIP  {model_id} ({entry.get('approval_status', 'quarantined')})")
            if selected:
                failures.append(f"{model_id}: not enabled for profile {args.profile}")
            continue
        if "archive" in entry:
            failures.extend(
                _process_archive(
                    entry,
                    args.models_dir,
                    cache_dir,
                    args.retries,
                    args.verify_only,
                )
            )
        else:
            failures.extend(
                _process_direct(
                    entry,
                    args.models_dir,
                    args.retries,
                    args.verify_only,
                    artifact_sources,
                )
            )

    unknown = selected - seen
    failures.extend(f"unknown model id: {model_id}" for model_id in sorted(unknown))
    if failures:
        for failure in failures:
            print(f"ERROR {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    raise SystemExit(main())
