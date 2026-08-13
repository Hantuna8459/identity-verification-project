from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from support.fake_providers import (
    FakeFailingProvider,
    FakeInvalidEvidenceProvider,
    FakeSlowProvider,
    FakeSuccessProvider,
)

from app.adapters.capability_registry import (
    CapabilityRegistry,
    CapabilityUnavailableError,
    ProviderRegistration,
)
from app.adapters.manifest import ManifestReader
from app.domain.capability_ports import ProviderChain


def _registration(provider: Any) -> ProviderRegistration:
    return ProviderRegistration(
        provider_id=provider.provider_id,
        capability="voice_challenge",
        factory=lambda p=provider: p,
        model_id=provider.model_id,
        adapter_spec_version=provider.adapter_spec_version,
        config_version="test-config/1",
    )


def _write_governance_manifest(
    tmp_path: Path, registrations: dict[str, ProviderRegistration]
) -> None:
    """Approve every fake provider used in a test, mirroring manifest.json's
    real `providers[]` governance array - tests exercise fallback/timeout/
    circuit-breaker mechanics, not the governance gate itself (that has its
    own dedicated negative test below)."""
    manifest_path = tmp_path / "manifest.json"
    if manifest_path.exists():
        return
    providers = [
        {
            "id": provider_id,
            "capability": registration.capability,
            "model_id": registration.model_id,
            "adapter_spec_version": registration.adapter_spec_version,
            "usage_scope": ["technical_demo"],
        }
        for provider_id, registration in registrations.items()
    ]
    manifest_path.write_text(json.dumps({"models": [], "providers": providers}))


def _registry(
    tmp_path: Path,
    chains: dict[str, ProviderChain],
    registrations: dict[str, ProviderRegistration],
    *,
    timeout_seconds: float = 5.0,
    circuit_failure_threshold: int = 3,
    circuit_cooldown_seconds: float = 60.0,
) -> CapabilityRegistry:
    _write_governance_manifest(tmp_path, registrations)
    manifest = ManifestReader(tmp_path, "technical_demo")
    return CapabilityRegistry(
        manifest,
        chains,  # type: ignore[arg-type]
        registrations,
        timeout_seconds=timeout_seconds,
        circuit_failure_threshold=circuit_failure_threshold,
        circuit_cooldown_seconds=circuit_cooldown_seconds,
    )


def test_config_swap_changes_which_provider_runs(tmp_path: Path) -> None:
    """Proves the M2 completion bar: swap a provider by composition/config alone."""
    primary = FakeSuccessProvider("fake-primary", {"status": "OK", "value": "A"})
    alternate = FakeSuccessProvider("fake-alternate", {"status": "OK", "value": "B"})
    registrations = {p.provider_id: _registration(p) for p in (primary, alternate)}

    registry_a = _registry(
        tmp_path, {"voice_challenge": ProviderChain(primary="fake-primary")}, registrations
    )
    result_a, attempts_a = registry_a.run("voice_challenge", None)
    assert result_a is not None and result_a["value"] == "A"
    assert attempts_a[0].provider_id == "fake-primary"

    registry_b = _registry(
        tmp_path, {"voice_challenge": ProviderChain(primary="fake-alternate")}, registrations
    )
    result_b, attempts_b = registry_b.run("voice_challenge", None)
    assert result_b is not None and result_b["value"] == "B"
    assert attempts_b[0].provider_id == "fake-alternate"


def test_primary_technical_failure_falls_back_to_secondary(tmp_path: Path) -> None:
    primary = FakeFailingProvider("fake-primary")
    secondary = FakeSuccessProvider("fake-secondary", {"status": "OK"})
    registrations = {p.provider_id: _registration(p) for p in (primary, secondary)}
    chain = {"voice_challenge": ProviderChain(primary="fake-primary", secondary="fake-secondary")}

    result, attempts = _registry(tmp_path, chain, registrations).run("voice_challenge", None)

    assert result == {"status": "OK"}
    assert [attempt.provider_role for attempt in attempts] == ["primary", "secondary"]
    assert attempts[0].status == "FAILED"
    assert attempts[1].status == "COMPLETED"


def test_all_providers_failing_returns_unavailable_without_raising(tmp_path: Path) -> None:
    primary = FakeFailingProvider("fake-primary")
    secondary = FakeFailingProvider("fake-secondary")
    registrations = {p.provider_id: _registration(p) for p in (primary, secondary)}
    chain = {"voice_challenge": ProviderChain(primary="fake-primary", secondary="fake-secondary")}

    result, attempts = _registry(tmp_path, chain, registrations).run("voice_challenge", None)

    assert result is None
    assert [attempt.status for attempt in attempts] == ["FAILED", "FAILED"]


def test_invalid_evidence_error_does_not_trigger_fallback(tmp_path: Path) -> None:
    """ADR-M0-002: no fallback for input-quality/business failures."""
    primary = FakeInvalidEvidenceProvider("fake-primary")
    secondary = FakeSuccessProvider("fake-secondary", {"status": "OK"})
    registrations = {p.provider_id: _registration(p) for p in (primary, secondary)}
    chain = {"voice_challenge": ProviderChain(primary="fake-primary", secondary="fake-secondary")}

    result, attempts = _registry(tmp_path, chain, registrations).run("voice_challenge", None)

    assert result is None
    assert len(attempts) == 1
    assert attempts[0].status == "INVALID_OUTPUT"
    assert secondary.calls == 0


def test_circuit_breaker_opens_after_consecutive_failures(tmp_path: Path) -> None:
    primary = FakeFailingProvider("fake-primary")
    registrations = {primary.provider_id: _registration(primary)}
    chain = {"voice_challenge": ProviderChain(primary="fake-primary")}
    registry = _registry(tmp_path, chain, registrations, circuit_failure_threshold=2)

    registry.run("voice_challenge", None)
    registry.run("voice_challenge", None)
    assert primary.calls == 2

    result, attempts = registry.run("voice_challenge", None)

    assert primary.calls == 2  # breaker skipped this call - provider not invoked again
    assert result is None
    assert attempts[0].status == "UNAVAILABLE"
    assert "PROVIDER_CIRCUIT_OPEN" in attempts[0].reason_codes


def test_slow_provider_times_out_and_falls_back(tmp_path: Path) -> None:
    primary = FakeSlowProvider("fake-primary", delay_seconds=0.3, result={"status": "OK"})
    secondary = FakeSuccessProvider("fake-secondary", {"status": "OK"})
    registrations = {p.provider_id: _registration(p) for p in (primary, secondary)}
    chain = {"voice_challenge": ProviderChain(primary="fake-primary", secondary="fake-secondary")}
    registry = _registry(tmp_path, chain, registrations, timeout_seconds=0.05)

    result, attempts = registry.run("voice_challenge", None)

    assert result == {"status": "OK"}
    assert attempts[0].status == "TIMEOUT"
    assert attempts[1].status == "COMPLETED"


def test_capability_without_chain_reports_not_registered(tmp_path: Path) -> None:
    registry = _registry(tmp_path, {}, {})

    readiness = registry.readiness()

    assert readiness["document_quality"]["status"] == "NOT_REGISTERED"
    assert readiness["speech_verification"]["status"] == "NOT_REGISTERED"
    result, attempts = registry.run("document_quality", None)
    assert result is None
    assert attempts == []


def test_resolve_raises_when_capability_not_registered(tmp_path: Path) -> None:
    registry = _registry(tmp_path, {}, {})

    with pytest.raises(CapabilityUnavailableError):
        registry.resolve("face_detection")


def test_provider_missing_governance_entry_fails_closed(tmp_path: Path) -> None:
    """Being wired in code (a ProviderRegistration exists) is not enough -
    without a governance entry at all in manifest.json's `providers[]`, the
    provider must never be invoked. No manifest.json is written for this
    test, so `fake-ungoverned` has no governance record at all."""
    provider = FakeSuccessProvider("fake-ungoverned", {"status": "OK"})
    registrations = {provider.provider_id: _registration(provider)}
    chain = {"voice_challenge": ProviderChain(primary="fake-ungoverned")}
    manifest = ManifestReader(tmp_path, "technical_demo")
    registry = CapabilityRegistry(
        manifest,
        chain,  # type: ignore[arg-type]
        registrations,
        timeout_seconds=5.0,
        circuit_failure_threshold=3,
        circuit_cooldown_seconds=60.0,
    )

    result, attempts = registry.run("voice_challenge", None)

    assert result is None
    assert provider.calls == 0
    assert attempts[0].status == "UNAVAILABLE"
    assert "fake-ungoverned:not_found" in attempts[0].reason_codes
