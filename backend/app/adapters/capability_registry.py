from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, get_args

from ai_modules.ekyc.errors import InvalidEvidenceError
from app.adapters.manifest import ManifestReader
from app.domain.capability_ports import (
    Attempt,
    AttemptStatus,
    CapabilityName,
    CapabilityProvider,
    ProviderChain,
    ProviderRole,
)

ALL_CAPABILITIES: tuple[CapabilityName, ...] = get_args(CapabilityName)


class CapabilityUnavailableError(RuntimeError):
    """Raised by `CapabilityRegistry.resolve()` when a directly-held provider
    (face_detection/face_embedding today) cannot be used this call."""

    def __init__(self, capability: str, reason: str) -> None:
        super().__init__(f"{capability} unavailable: {reason}")
        self.capability = capability
        self.reason = reason


@dataclass(frozen=True)
class ProviderRegistration:
    provider_id: str
    capability: CapabilityName
    factory: Callable[[], CapabilityProvider[Any, Any]]
    model_id: str | None
    adapter_spec_version: str
    config_version: str


class _CircuitBreaker:
    """Per-provider consecutive-failure breaker.

    In-memory and per-process only - a known limitation if this ever runs as
    multiple backend replicas (state would not be shared).
    """

    def __init__(self, failure_threshold: int, cooldown_seconds: float) -> None:
        self._failure_threshold = max(1, failure_threshold)
        self._cooldown_seconds = max(0.0, cooldown_seconds)
        self._lock = threading.Lock()
        self._failures: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}

    def is_open(self, provider_id: str) -> bool:
        with self._lock:
            opened_at = self._opened_at.get(provider_id)
            if opened_at is None:
                return False
            if time.monotonic() - opened_at >= self._cooldown_seconds:
                self._opened_at.pop(provider_id, None)
                self._failures[provider_id] = 0
                return False
            return True

    def record_success(self, provider_id: str) -> None:
        with self._lock:
            self._failures[provider_id] = 0
            self._opened_at.pop(provider_id, None)

    def record_failure(self, provider_id: str) -> None:
        with self._lock:
            failures = self._failures.get(provider_id, 0) + 1
            self._failures[provider_id] = failures
            if failures >= self._failure_threshold:
                self._opened_at[provider_id] = time.monotonic()


class CapabilityRegistry:
    """Composition-root provider registry (ADR-M0-001/ADR-M0-002).

    Orchestration code never constructs a provider directly - it calls
    `.run(capability, request)` and gets back the winning result (or `None`
    if every configured provider failed) plus the full `attempts` list, or
    `.resolve(capability)` for the small set of providers (face_detection,
    face_embedding) that are called many times per session as internal
    plumbing rather than once as a reportable capability result.
    """

    def __init__(
        self,
        manifest: ManifestReader,
        chains: dict[CapabilityName, ProviderChain],
        registrations: dict[str, ProviderRegistration],
        *,
        timeout_seconds: float,
        circuit_failure_threshold: int,
        circuit_cooldown_seconds: float,
    ) -> None:
        self._manifest = manifest
        self._chains = chains
        self._registrations = registrations
        self._timeout_seconds = timeout_seconds
        self._circuit = _CircuitBreaker(circuit_failure_threshold, circuit_cooldown_seconds)
        self._instances: dict[str, CapabilityProvider[Any, Any]] = {}
        self._instance_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="capability-provider")

    @property
    def manifest(self) -> ManifestReader:
        return self._manifest

    def registrations(self) -> dict[str, ProviderRegistration]:
        """Read-only view of the full code-registered provider catalog,
        independent of which chains/capabilities currently reference them.
        Used by scripts/validate_capability_providers.py to check every
        registered provider has a governance entry, not just active ones."""
        return dict(self._registrations)

    # -- shared plumbing -----------------------------------------------

    def _provider(self, provider_id: str) -> CapabilityProvider[Any, Any]:
        with self._instance_lock:
            instance = self._instances.get(provider_id)
            if instance is None:
                instance = self._registrations[provider_id].factory()
                self._instances[provider_id] = instance
            return instance

    def _manifest_ready(self, registration: ProviderRegistration) -> tuple[bool, list[str]]:
        """Two locks, checked in order: the provider's own governance record
        (is *this adapter* registered to run at all, in this profile - not
        just "does the code exist"), then its backing model's artifact
        validity (unchanged from before). Being wired in `ekyc_providers.py`
        is necessary but no longer sufficient for a provider to be invoked.
        """
        governed, governance_invalid = self._manifest.provider_ready(registration.provider_id)
        if not governed:
            return False, governance_invalid
        return self._manifest.model_ready(registration.model_id)

    @staticmethod
    def _roles(chain: ProviderChain) -> list[tuple[ProviderRole, str]]:
        roles: list[tuple[ProviderRole, str]] = [("primary", chain.primary)]
        if chain.secondary:
            roles.append(("secondary", chain.secondary))
        return roles

    def _build_attempt(
        self,
        registration: ProviderRegistration,
        role: ProviderRole,
        *,
        started_at: datetime,
        duration_ms: int,
        status: AttemptStatus,
        reason_codes: list[str] | None = None,
    ) -> Attempt:
        return Attempt(
            provider_id=registration.provider_id,
            provider_role=role,
            model_id=registration.model_id,
            model_revision=self._manifest.model_revision(registration.model_id),
            manifest_entry_id=registration.model_id,
            adapter_spec_version=registration.adapter_spec_version,
            config_version=registration.config_version,
            started_at=started_at,
            duration_ms=duration_ms,
            status=status,
            reason_codes=reason_codes or [],
        )

    @staticmethod
    def _missing_attempt(provider_id: str, role: ProviderRole) -> Attempt:
        return Attempt(
            provider_id=provider_id,
            provider_role=role,
            model_id=None,
            model_revision=None,
            manifest_entry_id=None,
            adapter_spec_version="unknown",
            config_version="unknown",
            started_at=datetime.now(UTC),
            duration_ms=0,
            status="UNAVAILABLE",
            reason_codes=["PROVIDER_NOT_REGISTERED"],
        )

    # -- public API -------------------------------------------------------

    def run(self, capability: CapabilityName, request: Any) -> tuple[Any | None, list[Attempt]]:
        """Run `capability` through its configured provider chain.

        Returns `(result, attempts)`. `result` is `None` when every attempt
        failed (technical failure) or the primary attempt raised
        `InvalidEvidenceError` (business/input-quality failure, not
        fallback-eligible per ADR-M0-002) - callers build their own
        `{"status": ...}` fallback dict from `attempts`, matching the shape
        of an actual provider result.
        """
        chain = self._chains.get(capability)
        if chain is None:
            return None, []

        attempts: list[Attempt] = []
        for role, provider_id in self._roles(chain):
            registration = self._registrations.get(provider_id)
            if registration is None:
                attempts.append(self._missing_attempt(provider_id, role))
                continue

            if self._circuit.is_open(provider_id):
                attempts.append(
                    self._build_attempt(
                        registration,
                        role,
                        started_at=datetime.now(UTC),
                        duration_ms=0,
                        status="UNAVAILABLE",
                        reason_codes=["PROVIDER_CIRCUIT_OPEN"],
                    )
                )
                continue

            ready, invalid_reasons = self._manifest_ready(registration)
            if not ready:
                attempts.append(
                    self._build_attempt(
                        registration,
                        role,
                        started_at=datetime.now(UTC),
                        duration_ms=0,
                        status="UNAVAILABLE",
                        reason_codes=invalid_reasons or ["REQUIRED_MODEL_ARTIFACT_INVALID"],
                    )
                )
                continue

            started_at = datetime.now(UTC)
            start = time.monotonic()
            try:
                provider = self._provider(provider_id)
                future = self._executor.submit(provider.run, request)
                result = future.result(timeout=self._timeout_seconds)
            except InvalidEvidenceError as exc:
                duration_ms = int((time.monotonic() - start) * 1000)
                attempts.append(
                    self._build_attempt(
                        registration,
                        role,
                        started_at=started_at,
                        duration_ms=duration_ms,
                        status="INVALID_OUTPUT",
                        reason_codes=[type(exc).__name__],
                    )
                )
                return None, attempts
            except FutureTimeoutError:
                duration_ms = int((time.monotonic() - start) * 1000)
                attempts.append(
                    self._build_attempt(
                        registration,
                        role,
                        started_at=started_at,
                        duration_ms=duration_ms,
                        status="TIMEOUT",
                        reason_codes=["PROVIDER_TIMEOUT"],
                    )
                )
                self._circuit.record_failure(provider_id)
                continue
            except Exception as exc:  # technical failure: fallback-eligible
                duration_ms = int((time.monotonic() - start) * 1000)
                attempts.append(
                    self._build_attempt(
                        registration,
                        role,
                        started_at=started_at,
                        duration_ms=duration_ms,
                        status="FAILED",
                        reason_codes=[type(exc).__name__],
                    )
                )
                self._circuit.record_failure(provider_id)
                continue
            else:
                duration_ms = int((time.monotonic() - start) * 1000)
                self._circuit.record_success(provider_id)
                attempts.append(
                    self._build_attempt(
                        registration,
                        role,
                        started_at=started_at,
                        duration_ms=duration_ms,
                        status="COMPLETED",
                    )
                )
                return result, attempts

        return None, attempts

    def resolve(self, capability: CapabilityName) -> CapabilityProvider[Any, Any]:
        """Return the primary provider instance for direct, repeated use.

        Used only for `face_detection`/`face_embedding`, which are called
        many times per session (once per sampled frame) as internal plumbing
        for face_matching/passive_liveness/visual_deepfake/active_liveness/
        replay_attack/camera_injection rather than once as their own
        reportable capability result - routing every one of those calls
        through `.run()` would multiply attempts per frame instead of once
        per session. No fallback/circuit/timeout wrapping applies here;
        callers are expected to wrap their own error handling the same way
        the previous single shared-engine pipeline did.
        """
        chain = self._chains.get(capability)
        if chain is None:
            raise CapabilityUnavailableError(capability, "CAPABILITY_NOT_REGISTERED")
        registration = self._registrations.get(chain.primary)
        if registration is None:
            raise CapabilityUnavailableError(capability, "PROVIDER_NOT_REGISTERED")
        ready, invalid_reasons = self._manifest_ready(registration)
        if not ready:
            reason = invalid_reasons[0] if invalid_reasons else "REQUIRED_MODEL_ARTIFACT_INVALID"
            raise CapabilityUnavailableError(capability, reason)
        return self._provider(registration.provider_id)

    def readiness(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for capability in ALL_CAPABILITIES:
            chain = self._chains.get(capability)
            if chain is None:
                result[capability] = {"registered": False, "status": "NOT_REGISTERED"}
                continue
            roles: dict[str, Any] = {}
            for role, provider_id in self._roles(chain):
                registration = self._registrations.get(provider_id)
                if registration is None:
                    roles[role] = {
                        "provider_id": provider_id,
                        "ready": False,
                        "invalid": ["PROVIDER_NOT_REGISTERED"],
                    }
                    continue
                ready, invalid_reasons = self._manifest_ready(registration)
                roles[role] = {
                    "provider_id": provider_id,
                    "model_id": registration.model_id,
                    "ready": ready,
                    "invalid": invalid_reasons,
                }
            result[capability] = {"registered": True, "status": "REGISTERED", **roles}
        return result
