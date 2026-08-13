from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REGISTRY_PATH = Path(__file__).resolve().parent / "datasets" / "registry.json"

# Field set per the dataset registry schema in
# docs/M0_CONTRACT_GOVERNANCE_BASELINE.md section 6. Records document
# provenance/license/sensitivity for legal-risk tracking (`notes`) - nothing
# here gates whether a dataset can be used in a benchmark run.
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
    "notes",
}


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
            )
        )
    return records


def get_dataset(
    dataset_id: str, *, capability: str, registry_path: Path = _REGISTRY_PATH
) -> DatasetRecord:
    """Look up a registered dataset for `capability`. Raises if the dataset
    isn't registered at all, or isn't registered for this capability - those
    are reference-integrity checks, not a license/approval gate."""
    for record in load_all(registry_path):
        if record.dataset_id != dataset_id:
            continue
        if capability not in record.capabilities:
            raise RuntimeError(f"{dataset_id}: not registered for capability {capability!r}")
        return record
    raise RuntimeError(f"{dataset_id}: not found in dataset registry")


def as_report_fields(record: DatasetRecord) -> dict[str, Any]:
    return {
        "dataset_id": record.dataset_id,
        "name": record.name,
        "version": record.version,
        "split_policy": record.split_policy,
        "sensitivity": record.sensitivity,
    }
