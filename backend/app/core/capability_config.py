from __future__ import annotations

from app.core.config import Settings
from app.domain.capability_ports import CapabilityName, ProviderChain

# Versioned policy: changing which provider a capability resolves to (or
# bumping this version) is what ADR-M0-004 calls "changing config" - it
# invalidates any threshold computed against the old provider/model for the
# affected capability until benchmarked again.
CAPABILITY_PROVIDER_CONFIG_VERSION = "capability-providers/2026-08-13"

# capability -> Settings field holding "primary[,secondary]" provider id.
# `speech_verification` has no implementation yet and is intentionally
# absent here - CapabilityRegistry reports it NOT_REGISTERED rather than
# pointing at a fake provider.
_CAPABILITY_SETTINGS_FIELDS: dict[CapabilityName, str] = {
    "document_ocr": "provider_document_ocr",
    "document_layout": "provider_document_layout",
    "document_quality": "provider_document_quality",
    "passport_mrz": "provider_passport_mrz",
    "face_detection": "provider_face_detection",
    "face_embedding": "provider_face_embedding",
    "face_matching": "provider_face_matching",
    "passive_liveness": "provider_passive_liveness",
    "active_liveness": "provider_active_liveness",
    "visual_deepfake": "provider_visual_deepfake",
    "voice_challenge": "provider_voice_challenge",
    "lip_sync": "provider_lip_sync",
    "replay_attack": "provider_replay_attack",
    "camera_injection": "provider_camera_injection",
}


def _parse_chain(value: str) -> ProviderChain:
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        raise ValueError("Provider selection must name at least a primary provider id")
    primary, *rest = parts
    return ProviderChain(primary=primary, secondary=rest[0] if rest else None)


def build_provider_chains(settings: Settings) -> dict[CapabilityName, ProviderChain]:
    """Capability -> primary/secondary provider id, read from environment
    config (`Settings.provider_*`) rather than hardcoded here.

    Each deployment (technical-demo, pilot, production, ...) supplies its own
    `.env` with the provider ids appropriate for that environment; this
    function does not itself branch on `settings.model_profile` - the
    manifest's `usage_scope` gate (via `ManifestReader`) already fails a
    provider closed if it isn't registered for the active profile, so there
    is no separate profile table to keep in sync here.
    """
    return {
        capability: _parse_chain(getattr(settings, field_name))
        for capability, field_name in _CAPABILITY_SETTINGS_FIELDS.items()
    }
