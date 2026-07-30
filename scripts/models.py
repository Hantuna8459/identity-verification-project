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
from pathlib import Path
from typing import Any

CHUNK_SIZE = 1024 * 1024


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            value.update(chunk)
    return value.hexdigest()


def validate(path: Path, entry: dict[str, Any]) -> str | None:
    if not path.is_file():
        return "missing"
    expected_size = int(entry["size_bytes"])
    if path.stat().st_size != expected_size:
        return f"size mismatch ({path.stat().st_size} != {expected_size})"
    actual = digest(path)
    if actual != entry["sha256"]:
        return f"sha256 mismatch ({actual})"
    return None


def download(entry: dict[str, Any], destination: Path, retries: int) -> None:
    url = entry.get("url")
    if not url:
        raise RuntimeError(
            f"{entry['id']} has no public URL; provide the pinned project artifact at {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        temporary: Path | None = None
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "vid-ekyc-models/1.0"})
            with urllib.request.urlopen(request, timeout=300) as response:
                with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
                    temporary = Path(output.name)
                    while chunk := response.read(CHUNK_SIZE):
                        output.write(chunk)
            temporary.replace(destination)
            destination.chmod(0o644)
            return
        except Exception as exc:
            last_error = exc
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            if attempt < retries:
                time.sleep(min(2**attempt, 15))
    raise RuntimeError(f"Failed to download {entry['id']}: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and verify pinned V-ID eKYC models")
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--manifest", type=Path, default=Path("models/manifest.json"))
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Only process the given model id; may be repeated",
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        metavar="MODEL_ID=PATH",
        help="Provide a local artifact for a model without a download URL",
    )
    args = parser.parse_args()

    artifact_sources: dict[str, Path] = {}
    for value in args.artifact:
        model_id, separator, raw_path = value.partition("=")
        if not separator or not model_id or not raw_path:
            parser.error(f"Invalid --artifact value: {value!r}; expected MODEL_ID=PATH")
        artifact_sources[model_id] = Path(raw_path)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    failures: list[str] = []
    selected = set(args.include)
    for entry in manifest["models"]:
        if selected and entry["id"] not in selected:
            continue
        destination = args.models_dir / entry["path"]
        issue = validate(destination, entry)
        if issue and entry["id"] in artifact_sources:
            source = artifact_sources[entry["id"]]
            if not source.is_file():
                failures.append(f"{entry['id']}: local artifact missing: {source}")
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            destination.chmod(0o644)
            issue = validate(destination, entry)
        if issue and not args.verify_only:
            print(f"FETCH {entry['id']}: {issue}")
            try:
                download(entry, destination, args.retries)
            except RuntimeError as exc:
                failures.append(str(exc))
                continue
            issue = validate(destination, entry)
        if issue:
            failures.append(f"{entry['id']}: {issue}")
        else:
            print(f"OK    {entry['id']} ({destination.stat().st_size} bytes)")

    if failures:
        for failure in failures:
            print(f"ERROR {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    raise SystemExit(main())
