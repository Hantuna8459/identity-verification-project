from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_validator() -> Any:
    script = Path(__file__).parents[2] / "scripts/validate_capability_providers.py"
    spec = importlib.util.spec_from_file_location("validate_capability_providers", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_artifact_only_failure_is_classified_correctly() -> None:
    module = _load_validator()

    assert module._is_artifact_only_failure(["some-model:weights.onnx:missing"]) is True
    assert module._is_artifact_only_failure(["some-model:weights.onnx:size"]) is True
    assert module._is_artifact_only_failure(["some-model:weights.onnx:sha256"]) is True
    assert module._is_artifact_only_failure([]) is False


def test_governance_failure_is_not_classified_as_artifact_only() -> None:
    module = _load_validator()

    assert module._is_artifact_only_failure(["some-provider:not_found"]) is False
    assert module._is_artifact_only_failure(["some-provider:not_approved_for_profile"]) is False
    assert module._is_artifact_only_failure(["PROVIDER_NOT_REGISTERED"]) is False
    # Mixed: one governance reason alongside an artifact one must still fail closed.
    assert module._is_artifact_only_failure(["x:not_found", "y:weights.onnx:missing"]) is False


def test_manifest_provider_ids_reads_providers_array(tmp_path: Path) -> None:
    module = _load_validator()
    (tmp_path / "manifest.json").write_text(json.dumps({"providers": [{"id": "a"}, {"id": "b"}]}))

    assert module._manifest_provider_ids(tmp_path) == {"a", "b"}


def test_manifest_provider_ids_empty_when_manifest_missing(tmp_path: Path) -> None:
    module = _load_validator()

    assert module._manifest_provider_ids(tmp_path) == set()
