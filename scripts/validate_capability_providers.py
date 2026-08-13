#!/usr/bin/env python3
"""Cross-check capability -> provider wiring across all three layers before
you ever boot the app: env-selected chains (.env / Settings.provider_*),
manifest.json governance (providers[]), and code registration
(backend/app/adapters/ekyc_providers.py).

Usage (from repo root):
    python3 scripts/validate_capability_providers.py
    python3 scripts/validate_capability_providers.py --require-artifacts
    python3 scripts/validate_capability_providers.py --profile pilot --model-dir /path/to/models

Exit 0 = every code-registered provider has a governance entry, and every
currently-configured chain (per Settings.provider_*) resolves to a real,
approved provider. Artifact presence/hash on disk is only checked when
--require-artifacts is passed - a dev machine or CI box without the ~1GB of
downloaded model weights is not a validation failure by default.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.adapters.ekyc_providers import build_capability_registry  # noqa: E402
from app.core.config import Settings  # noqa: E402

ARTIFACT_ONLY_SUFFIXES = (":missing", ":size", ":sha256")


def _is_artifact_only_failure(invalid: list[str]) -> bool:
    return bool(invalid) and all(reason.endswith(ARTIFACT_ONLY_SUFFIXES) for reason in invalid)


def _manifest_provider_ids(model_dir: Path) -> set[str]:
    manifest_path = model_dir / "manifest.json"
    if not manifest_path.is_file():
        return set()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {str(entry.get("id")) for entry in data.get("providers", [])}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--profile", default=None, help="Override MODEL_PROFILE")
    parser.add_argument("--model-dir", default=None, help="Override MODEL_DIR")
    parser.add_argument(
        "--require-artifacts",
        action="store_true",
        help="Also fail on missing/invalid model artifact files on disk (off by default)",
    )
    args = parser.parse_args()

    overrides: dict[str, Any] = {}
    if args.profile:
        overrides["model_profile"] = args.profile
    if args.model_dir:
        overrides["model_dir"] = Path(args.model_dir)
    settings = Settings(**overrides)

    registry = build_capability_registry(settings)
    registrations = registry.registrations()
    readiness = registry.readiness()
    governance_ids = _manifest_provider_ids(settings.model_dir)

    governance_failures: list[str] = []
    artifact_failures: list[str] = []
    warnings: list[str] = []

    print(f"Profile: {settings.model_profile}   Model dir: {settings.model_dir}\n")

    # 1. Every provider wired in code has a governance entry, regardless of
    #    whether any chain currently points at it - catches "wrote the class,
    #    forgot the manifest entry" before you ever touch .env.
    print("-- Code-registered providers --")
    for provider_id, registration in sorted(registrations.items()):
        ready, invalid = registry.manifest.provider_ready(provider_id)
        if ready:
            capability = registration.capability
            print(f"  OK    {provider_id:35s} capability={capability:20s}")
        else:
            governance_failures.append(f"{provider_id}: {', '.join(invalid)}")
            print(f"  FAIL  {provider_id:35s} capability={registration.capability:20s} {invalid}")

    # 2. Every currently-configured chain (what .env actually selects) resolves.
    print("\n-- Configured chains (capability -> active provider) --")
    for capability, entry in sorted(readiness.items()):
        if not entry["registered"]:
            print(f"  --    {capability:20s} NOT_REGISTERED (no chain configured)")
            continue
        for role in ("primary", "secondary"):
            role_info = entry.get(role)
            if role_info is None:
                continue
            label = f"{capability}.{role}"
            if role_info["ready"]:
                print(f"  OK    {label:30s} {role_info['provider_id']}")
                continue
            invalid = role_info["invalid"]
            if _is_artifact_only_failure(invalid):
                message = f"{label}: {role_info['provider_id']}: {invalid}"
                if args.require_artifacts:
                    artifact_failures.append(message)
                    print(f"  FAIL  {label:30s} {role_info['provider_id']} (artifact) {invalid}")
                else:
                    provider_id = role_info["provider_id"]
                    print(f"  SKIP  {label:30s} {provider_id} (artifact, not checked) {invalid}")
            else:
                governance_failures.append(f"{label}: {role_info['provider_id']}: {invalid}")
                print(f"  FAIL  {label:30s} {role_info['provider_id']} {invalid}")

    # 3. Governance entries with no matching code registration - dead weight,
    #    or a provider that was removed from code without cleaning up.
    orphaned = sorted(governance_ids - set(registrations))
    if orphaned:
        warnings.extend(
            f"manifest.json#providers[] entry with no code registration: {pid}" for pid in orphaned
        )

    if warnings:
        print("\n-- Warnings --")
        for warning in warnings:
            print(f"  WARN  {warning}")

    failures = governance_failures + artifact_failures
    if failures:
        print(f"\n{len(failures)} problem(s) found:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nOK: every provider is governance-approved and every configured chain resolves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
