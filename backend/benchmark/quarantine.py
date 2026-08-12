from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "models" / "manifest.json"

# Candidate models that exist in models/manifest.json for a capability but are
# not the active provider - kept here so a benchmark report says explicitly
# which ones were excluded and why, instead of silently only ever covering
# the active provider.
CAPABILITY_CANDIDATE_MODELS: dict[str, tuple[str, ...]] = {
    "document_ocr": ("vietocr-vgg-transformer",),
}

_BLOCKED_STATUSES = {"quarantined", "rejected"}


def model_entry(model_id: str, manifest_path: Path = _MANIFEST_PATH) -> dict[str, Any] | None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest.get("models", []):
        if entry.get("id") == model_id:
            return entry
    return None


def is_blocked(model_id: str, manifest_path: Path = _MANIFEST_PATH) -> bool:
    entry = model_entry(model_id, manifest_path)
    if entry is None:
        return True
    return entry.get("approval_status", "quarantined") in _BLOCKED_STATUSES


def skipped_models_for(
    capability: str, manifest_path: Path = _MANIFEST_PATH
) -> list[dict[str, Any]]:
    candidates = CAPABILITY_CANDIDATE_MODELS.get(capability, ())
    if not candidates:
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in manifest.get("models", [])}
    skipped = []
    for model_id in candidates:
        entry = by_id.get(model_id)
        if entry is None:
            continue
        status = entry.get("approval_status", "quarantined")
        if status not in _BLOCKED_STATUSES:
            continue
        skipped.append(
            {
                "model_id": model_id,
                "approval_status": status,
                "license": entry.get("license"),
                "distribution_permission": entry.get("distribution_permission"),
                "reason": (
                    f"Excluded from benchmark run: approval_status is {status!r} "
                    "(license/usage rights not established). Not downloaded, not "
                    "scored. Requires explicit license review and an "
                    "approval_status change in models/manifest.json before "
                    "inclusion."
                ),
            }
        )
    return skipped
