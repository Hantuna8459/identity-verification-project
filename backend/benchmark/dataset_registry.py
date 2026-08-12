from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REGISTRY_PATH = Path(__file__).resolve().parent / "datasets" / "registry.json"

# Field set per the dataset registry schema in
# docs/M0_CONTRACT_GOVERNANCE_BASELINE.md section 6.
_REQUIRED_FIELDS = {
    "dataset_id",
    "name",
    "version",
    "capabilities",
    "source_url",
    "source_type",
    "license_name",
    "license_url",
    "terms_summary",
    "distribution_permission",
    "usage_scope",
    "sensitivity",
    "storage_location",
    "checksum_sha256",
    "split_policy",
    "approval_status",
    "approval_owner",
    "approval_reference",
    "approved_at",
    "expires_at",
    "notes",
}

_APPROVED_STATUS = "approved_for_evaluation"


@dataclass(frozen=True)
class DatasetRecord:
    dataset_id: str
    name: str
    version: str
    capabilities: tuple[str, ...]
    source_type: str
    usage_scope: str
    sensitivity: str
    split_policy: str
    approval_status: str
    approval_reference: str | None


def load_all(registry_path: Path = _REGISTRY_PATH) -> list[DatasetRecord]:
    entries = json.loads(registry_path.read_text(encoding="utf-8"))
    records = []
    for entry in entries:
        missing = _REQUIRED_FIELDS - entry.keys()
        if missing:
            raise RuntimeError(
                f"{entry.get('dataset_id', '?')}: dataset registry entry missing fields "
                f"{sorted(missing)}"
            )
        records.append(
            DatasetRecord(
                dataset_id=entry["dataset_id"],
                name=entry["name"],
                version=entry["version"],
                capabilities=tuple(entry["capabilities"]),
                source_type=entry["source_type"],
                usage_scope=entry["usage_scope"],
                sensitivity=entry["sensitivity"],
                split_policy=entry["split_policy"],
                approval_status=entry["approval_status"],
                approval_reference=entry["approval_reference"],
            )
        )
    return records


def require_approved(
    dataset_id: str, *, capability: str, registry_path: Path = _REGISTRY_PATH
) -> DatasetRecord:
    """Fail closed: a benchmark runner may only use a dataset registered for
    its capability and explicitly `approved_for_evaluation`."""
    for record in load_all(registry_path):
        if record.dataset_id != dataset_id:
            continue
        if capability not in record.capabilities:
            raise RuntimeError(f"{dataset_id}: not registered for capability {capability!r}")
        if record.approval_status != _APPROVED_STATUS:
            raise RuntimeError(
                f"{dataset_id}: approval_status={record.approval_status!r}, refusing to "
                f"benchmark (fail-closed; only {_APPROVED_STATUS!r} datasets may run)"
            )
        return record
    raise RuntimeError(f"{dataset_id}: not found in dataset registry")


def as_report_fields(record: DatasetRecord) -> dict[str, Any]:
    return {
        "dataset_id": record.dataset_id,
        "name": record.name,
        "version": record.version,
        "split_policy": record.split_policy,
        "sensitivity": record.sensitivity,
        "approval_status": record.approval_status,
    }
