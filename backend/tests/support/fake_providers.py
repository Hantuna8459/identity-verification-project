from __future__ import annotations

import time
from typing import Any

from ai_modules.ekyc.errors import InvalidEvidenceError


class FakeSuccessProvider:
    def __init__(self, provider_id: str, result: Any, model_id: str | None = None) -> None:
        self.provider_id = provider_id
        self.model_id = model_id
        self.adapter_spec_version = "fake/1"
        self._result = result
        self.calls = 0

    def run(self, request: Any) -> Any:
        self.calls += 1
        return self._result


class FakeFailingProvider:
    """Always raises a technical (fallback-eligible) error."""

    def __init__(
        self, provider_id: str, model_id: str | None = None, exception: Exception | None = None
    ) -> None:
        self.provider_id = provider_id
        self.model_id = model_id
        self.adapter_spec_version = "fake/1"
        self._exception = exception or RuntimeError("simulated technical failure")
        self.calls = 0

    def run(self, request: Any) -> Any:
        self.calls += 1
        raise self._exception


class FakeInvalidEvidenceProvider:
    """Always raises InvalidEvidenceError (business/quality failure, not fallback-eligible)."""

    def __init__(self, provider_id: str, model_id: str | None = None) -> None:
        self.provider_id = provider_id
        self.model_id = model_id
        self.adapter_spec_version = "fake/1"
        self.calls = 0

    def run(self, request: Any) -> Any:
        self.calls += 1
        raise InvalidEvidenceError("simulated business/input-quality failure")


class FakeSlowProvider:
    """Sleeps past the caller's timeout budget before returning a result."""

    def __init__(
        self, provider_id: str, delay_seconds: float, result: Any, model_id: str | None = None
    ) -> None:
        self.provider_id = provider_id
        self.model_id = model_id
        self.adapter_spec_version = "fake/1"
        self._delay = delay_seconds
        self._result = result
        self.calls = 0

    def run(self, request: Any) -> Any:
        self.calls += 1
        time.sleep(self._delay)
        return self._result
