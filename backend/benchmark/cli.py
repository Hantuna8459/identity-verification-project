from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from benchmark import report
from benchmark.runners import (
    document_ocr_runner,
    lip_sync_runner,
    passport_mrz_runner,
    voice_challenge_runner,
)
from fieldcheck.paths import DEFAULT_LOCAL_CASES_DIR

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = BACKEND_DIR.parent / "models"
DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "reports"

_RUNNERS = {
    "document_ocr": lambda model_dir, cases_root, seed: document_ocr_runner.run(
        model_dir, seed=seed
    ),
    "passport_mrz": lambda model_dir, cases_root, seed: passport_mrz_runner.run(seed=seed),
    "voice_challenge": lambda model_dir, cases_root, seed: voice_challenge_runner.run(
        model_dir, cases_root
    ),
    "lip_sync": lambda model_dir, cases_root, seed: lip_sync_runner.run(model_dir, cases_root),
}


def _run_one(
    capability: str, model_dir: Path, cases_root: Path, seed: int, out_dir: Path
) -> Path:
    result = _RUNNERS[capability](model_dir, cases_root, seed)
    return report.write_report(result, out_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m benchmark.cli",
        description=(
            "V-ID eKYC benchmark CLI (M4). Runs independently of session state "
            "and the operational DB; never downloads models or datasets."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one or all benchmark suites")
    run_parser.add_argument(
        "--capability",
        choices=[*sorted(_RUNNERS), "all"],
        default="all",
    )
    run_parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    run_parser.add_argument("--cases-root", type=Path, default=DEFAULT_LOCAL_CASES_DIR)
    run_parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    run_parser.add_argument("--seed", type=int, default=20260811)

    args = parser.parse_args(argv)

    capabilities = sorted(_RUNNERS) if args.capability == "all" else [args.capability]
    for capability in capabilities:
        path = _run_one(capability, args.model_dir, args.cases_root, args.seed, args.out)
        summary = json.loads(path.read_text(encoding="utf-8"))
        print(f"{capability}: wrote {path}")
        print(json.dumps(summary["metrics"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
