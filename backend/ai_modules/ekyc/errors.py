from __future__ import annotations


class InvalidEvidenceError(ValueError):
    """Business/input-quality failure - never fallback-eligible (ADR-M0-002)."""
