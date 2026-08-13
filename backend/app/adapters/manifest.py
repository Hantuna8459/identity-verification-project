from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ManifestModelStatus:
    model_id: str
    revision: str | None
    in_scope: bool
    required: bool
    invalid: list[str] = field(default_factory=list)

    @property
    def artifact_ready(self) -> bool:
        return not self.invalid


@dataclass(frozen=True)
class ManifestSummary:
    manifest: bool
    model_ids: list[str]
    invalid: list[str]

    @property
    def artifact_ready(self) -> bool:
        return not self.invalid


@dataclass(frozen=True)
class ProviderGovernanceStatus:
    provider_id: str
    in_scope: bool


class ManifestReader:
    """Single source of truth for manifest-driven scope/artifact status.

    Gating is registration + `usage_scope` matching the active profile,
    nothing else. License/legal-risk classification for a model/provider
    lives in its manifest entry's `notes` field and in
    `docs/model_license_risk_matrix.html`, not in anything this class reads
    or returns.

    Shared by OfflineModelAnalyzer.readiness() (aggregate, backward-compatible
    shape) and CapabilityRegistry.readiness()/gating (per-model, per-provider).
    """

    def __init__(self, model_dir: Path, profile: str) -> None:
        self._model_dir = model_dir
        self._profile = profile
        self._raw: dict[str, Any] | None = None
        self._cache: dict[str, ManifestModelStatus] | None = None
        self._provider_cache: dict[str, ProviderGovernanceStatus] | None = None
        self._manifest_present = False

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _artifacts(entry: dict[str, Any]) -> list[dict[str, Any]]:
        artifacts = entry.get("artifacts")
        return artifacts if isinstance(artifacts, list) else [entry]

    def _read_manifest(self) -> dict[str, Any]:
        if self._raw is not None:
            return self._raw
        manifest_path = self._model_dir / "manifest.json"
        if not manifest_path.is_file():
            self._raw = {}
            return self._raw
        self._manifest_present = True
        self._raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        return self._raw

    def _in_scope(self, scopes: list[str]) -> bool:
        return self._profile in scopes or "all" in scopes

    def _load(self) -> dict[str, ManifestModelStatus]:
        if self._cache is not None:
            return self._cache
        statuses: dict[str, ManifestModelStatus] = {}
        data = self._read_manifest()
        for entry in data.get("models", []):
            model_id = str(entry.get("id", "unknown"))
            in_scope = self._in_scope(entry.get("usage_scope", []))
            required = bool(entry.get("required"))
            invalid: list[str] = []
            if in_scope and required:
                for artifact in self._artifacts(entry):
                    path = self._model_dir / str(artifact["path"])
                    label = f"{model_id}:{artifact['path']}"
                    if not path.is_file():
                        invalid.append(f"{label}:missing")
                    elif path.stat().st_size != int(artifact["size_bytes"]):
                        invalid.append(f"{label}:size")
                    elif self._sha256(path) != artifact["sha256"]:
                        invalid.append(f"{label}:sha256")
            revision = entry.get("revision")
            statuses[model_id] = ManifestModelStatus(
                model_id=model_id,
                revision=str(revision) if revision is not None else None,
                in_scope=in_scope,
                required=required,
                invalid=invalid,
            )
        self._cache = statuses
        return statuses

    def summary(self) -> ManifestSummary:
        statuses = self._load()
        in_scope = {model_id: status for model_id, status in statuses.items() if status.in_scope}
        invalid: list[str] = []
        for status in in_scope.values():
            invalid.extend(status.invalid)
        return ManifestSummary(
            manifest=self._manifest_present,
            model_ids=list(in_scope.keys()),
            invalid=invalid,
        )

    def model_ready(self, model_id: str | None) -> tuple[bool, list[str]]:
        """Return (ready, invalid_reasons) for a provider's backing model.

        `model_id=None` means the provider has no backing model artifact (a
        deterministic rule/heuristic) and is therefore always ready.
        """
        if model_id is None:
            return True, []
        status = self._load().get(model_id)
        if status is None:
            return False, [f"{model_id}:not_found"]
        if not status.in_scope:
            return False, [f"{model_id}:not_in_profile_scope"]
        return status.artifact_ready, list(status.invalid)

    def model_revision(self, model_id: str | None) -> str | None:
        if model_id is None:
            return None
        status = self._load().get(model_id)
        return status.revision if status is not None else None

    def _load_providers(self) -> dict[str, ProviderGovernanceStatus]:
        if self._provider_cache is not None:
            return self._provider_cache
        statuses: dict[str, ProviderGovernanceStatus] = {}
        data = self._read_manifest()
        for entry in data.get("providers", []):
            provider_id = str(entry.get("id", "unknown"))
            in_scope = self._in_scope(entry.get("usage_scope", []))
            statuses[provider_id] = ProviderGovernanceStatus(
                provider_id=provider_id,
                in_scope=in_scope,
            )
        self._provider_cache = statuses
        return statuses

    def provider_ready(self, provider_id: str) -> tuple[bool, list[str]]:
        """Return (ready, invalid_reasons) for a provider's own governance
        record - separate from whether its backing model's artifact is valid
        (see `model_ready`). A provider must be registered here with
        `usage_scope` covering the active profile, and have a ready model
        (if any), before CapabilityRegistry will invoke it: code
        registration in `ekyc_providers.py` alone is not enough, matching how
        `models[]` already gates a model's use.
        """
        status = self._load_providers().get(provider_id)
        if status is None:
            return False, [f"{provider_id}:not_found"]
        if not status.in_scope:
            return False, [f"{provider_id}:not_in_profile_scope"]
        return True, []
