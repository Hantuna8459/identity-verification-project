from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from app.adapters.capability_registry import CapabilityRegistry, ProviderRegistration
from app.adapters.manifest import ManifestReader
from app.domain.capability_ports import (
    ActiveLivenessResult,
    CameraInjectionResult,
    DocumentLayoutResult,
    DocumentOcrResult,
    FaceDetectionResult,
    FaceMatchingResult,
    LipSyncResult,
    PassiveLivenessResult,
    PassportMrzResult,
    ProviderChain,
    ReplayAttackResult,
    VisualDeepfakeResult,
    VoiceChallengeResult,
)
from support.fake_providers import FakeSuccessProvider

_ADAPTER_SPEC_VERSION = "fake/1"
_CONFIG_VERSION = "fake-config/1"


def _default_results() -> dict[str, Any]:
    """One successful typed *Result per capability EkycOrchestrator.analyze()
    actually touches (via .run() or .resolve()). face_embedding is excluded -
    it's only ever used internally by real providers' own composition, never
    called directly by the orchestrator (see capability_registry.py's
    docstring on resolve())."""
    return {
        "document_ocr": DocumentOcrResult(
            status="OK", engine="fake-ocr", line_count=1, mean_confidence=0.9, lines=["FAKE LINE"]
        ),
        "document_layout": DocumentLayoutResult(
            status="OK",
            engine="fake-layout",
            region_count=1,
            class_counts={"name": 1},
            ocr_line_count=1,
            mean_ocr_confidence=0.9,
        ),
        "passport_mrz": PassportMrzResult(
            status="OK",
            format="ICAO_TD3",
            mrz_detected=True,
            all_check_digits_valid=True,
            line_lengths=[44, 44],
            check_digits={"document_number": True},
        ),
        "face_detection": FaceDetectionResult(
            score=0.99,
            bbox=np.array([0.0, 0.0, 16.0, 16.0]),
            # Non-degenerate 5-point SCRFD landmarks (left eye, right eye,
            # nose, mouth corners) - a zeroed/degenerate eye distance makes
            # ai_modules.ekyc.active_liveness.estimate_head_yaw() raise
            # InvalidEvidenceError, which isn't what "the fake succeeded"
            # should mean here.
            landmarks=np.array(
                [[4.0, 6.0], [12.0, 6.0], [8.0, 10.0], [5.0, 13.0], [11.0, 13.0]]
            ),
        ),
        "face_matching": FaceMatchingResult(
            status="OK",
            engine="fake-match",
            cosine_similarity=0.8,
            sampled_frames=3,
            frames_with_face=3,
            matched_frames=3,
            aggregation="median",
        ),
        "passive_liveness": PassiveLivenessResult(
            status="OK", engine="fake-liveness", live_probability=0.95
        ),
        "active_liveness": ActiveLivenessResult(
            status="OK",
            engine="fake-active-liveness",
            sequence_complete=True,
            completed_step_count=3,
            required_step_count=3,
            sampled_pose_count=3,
        ),
        "visual_deepfake": VisualDeepfakeResult(
            status="OK", engine="fake-deepfake", manipulation_probability=0.05
        ),
        "voice_challenge": VoiceChallengeResult(
            status="OK",
            engine="fake-voice",
            challenge_length=6,
            recognized_digit_count=6,
            similarity=1.0,
        ),
        "lip_sync": LipSyncResult(
            status="OK",
            engine="fake-lipsync",
            verdict="real",
            confidence=0.9,
            manipulation_probability=0.1,
        ),
        "replay_attack": ReplayAttackResult(
            status="OK",
            engine="fake-replay",
            score=0.1,
            threshold=0.62,
            confirmed=False,
            duplicate_pairs=0,
            warnings=[],
        ),
        "camera_injection": CameraInjectionResult(
            status="OK",
            engine="fake-camera",
            score=0.1,
            threshold=0.60,
            suspicious=False,
            metadata_score=0.1,
            challenge_timing_score=0.1,
            duplication_score=0.1,
            reason_codes=[],
            warnings=[],
            sampled_frame_count=3,
        ),
    }


def build_fake_registry(
    tmp_path: Path, *, overrides: dict[str, Any] | None = None
) -> CapabilityRegistry:
    """A CapabilityRegistry wired with a FakeSuccessProvider per capability,
    each pre-approved in a hand-written manifest.json - same pattern as
    tests/test_capability_registry.py, generalized to cover the full set
    EkycOrchestrator.analyze() needs so fieldcheck's runner/CLI can be tested
    end-to-end with zero real models."""
    results = _default_results()
    if overrides:
        results.update(overrides)

    registrations: dict[str, ProviderRegistration] = {}
    chains: dict[str, ProviderChain] = {}
    for capability, result in results.items():
        provider_id = f"fake-{capability}"
        provider = FakeSuccessProvider(provider_id, result)
        registrations[provider_id] = ProviderRegistration(
            provider_id=provider_id,
            capability=capability,  # type: ignore[arg-type]
            factory=(lambda p=provider: p),
            model_id=None,
            adapter_spec_version=_ADAPTER_SPEC_VERSION,
            config_version=_CONFIG_VERSION,
        )
        chains[capability] = ProviderChain(primary=provider_id)

    manifest_path = tmp_path / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    providers = [
        {
            "id": registration.provider_id,
            "capability": registration.capability,
            "model_id": registration.model_id,
            "adapter_spec_version": registration.adapter_spec_version,
            "usage_scope": ["technical_demo"],
        }
        for registration in registrations.values()
    ]
    manifest_path.write_text(json.dumps({"models": [], "providers": providers}))

    manifest = ManifestReader(tmp_path, "technical_demo")
    return CapabilityRegistry(
        manifest,
        chains,  # type: ignore[arg-type]
        registrations,
        timeout_seconds=5.0,
        circuit_failure_threshold=3,
        circuit_cooldown_seconds=60.0,
    )
