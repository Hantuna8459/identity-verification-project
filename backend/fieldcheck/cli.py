from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from app.core.config import Settings
from fieldcheck import report
from fieldcheck.aggregate import aggregate
from fieldcheck.cases import CaseLoadError, discover_cases, load_case
from fieldcheck.paths import DEFAULT_LOCAL_CASES_DIR, DEFAULT_MODEL_DIR
from fieldcheck.render import print_aggregate, print_case_result, print_readiness
from fieldcheck.runner import CaseRunResult, build_analyzer, run_case


def _build_settings(model_dir: Path, profile: str) -> Settings:
    return Settings(model_dir=model_dir, model_profile=profile)


def _run_adhoc(args: argparse.Namespace) -> int:
    settings = _build_settings(args.model_dir, args.profile)
    analyzer = build_analyzer(settings)
    print_readiness(analyzer.readiness())

    try:
        case = load_case(args.case)
    except CaseLoadError as exc:
        print(f"error loading case {args.case}: {exc}", file=sys.stderr)
        return 1

    if args.document_type:
        case = dataclasses.replace(case, document_type=args.document_type)
    if args.voice_challenge is not None:
        case = dataclasses.replace(case, voice_challenge=args.voice_challenge)

    # Resolve the output path (and fail fast on an unsafe --out) before
    # spending time running the pipeline.
    out_path = report.resolve_output_path(args.out, stem=f"adhoc-{case.case_id}", force=args.force)

    result = run_case(analyzer, case)
    print_case_result(result)
    if args.json:
        print(json.dumps(result.result, indent=2, ensure_ascii=False, default=str))

    if result.status == "RAN":
        report.write_json(result.result, out_path)
        print(f"wrote {out_path}")
        return 0
    return 1


def _run_batch(args: argparse.Namespace) -> int:
    settings = _build_settings(args.model_dir, args.profile)
    analyzer = build_analyzer(settings)
    print_readiness(analyzer.readiness())

    case_dirs = discover_cases(args.cases_root, args.pattern)
    if not case_dirs:
        print(f"no case directories found under {args.cases_root}", file=sys.stderr)
        return 1

    out_dir = report.resolve_output_dir(args.out_dir, force=args.force)

    results: list[CaseRunResult] = []
    for case_dir in case_dirs:
        try:
            case = load_case(case_dir)
        except CaseLoadError as exc:
            result = CaseRunResult(case_id=case_dir.name, status="LOAD_FAILED", error=str(exc))
        else:
            result = run_case(analyzer, case)
        print_case_result(result)
        results.append(result)

        if args.save_per_case and result.status == "RAN":
            report.write_json(result.result, out_dir / "cases" / f"{result.case_id}.json")
        if args.fail_fast and result.status != "RAN":
            print(f"stopping (--fail-fast) after case {result.case_id!r}", file=sys.stderr)
            break

    summary = aggregate(results)
    print_aggregate(summary)
    summary_path = report.write_json(summary, out_dir / "summary.json")
    print(f"wrote {summary_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m fieldcheck.cli",
        description=(
            "Dev-only tool: run the real eKYC AI pipeline against your own real evidence "
            "(NOT the M4 governed dataset benchmark - see backend/benchmark/ for that). "
            "Never commit case directories or run output; local_cases/ and local_runs/ are "
            "both gitignored."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    common.add_argument("--profile", default="technical_demo")
    common.add_argument(
        "--force", action="store_true", help="allow writing output inside the git repository"
    )

    adhoc = subparsers.add_parser(
        "adhoc", parents=[common], help="Run one real evidence case and print/save the result"
    )
    adhoc.add_argument("--case", type=Path, required=True, help="case directory")
    adhoc.add_argument(
        "--document-type", default=None, help="override auto-detected document_type"
    )
    adhoc.add_argument(
        "--voice-challenge", default=None, help="override case.json's voice_challenge"
    )
    adhoc.add_argument(
        "--out", type=Path, default=None, help="output JSON path (default: local_runs/)"
    )
    adhoc.add_argument(
        "--json", action="store_true", help="also print the full result JSON to stdout"
    )

    batch = subparsers.add_parser(
        "batch",
        parents=[common],
        help="Run every case under a root directory and aggregate results",
    )
    batch.add_argument("--cases-root", type=Path, default=DEFAULT_LOCAL_CASES_DIR)
    batch.add_argument("--pattern", default="*", help="glob filter on case directory names")
    batch.add_argument("--fail-fast", action="store_true")
    batch.add_argument(
        "--out-dir", type=Path, default=None, help="output dir (default: local_runs/<ts>/)"
    )
    batch.add_argument(
        "--save-per-case", action="store_true", help="also write each case's full result JSON"
    )

    args = parser.parse_args(argv)
    if args.command == "adhoc":
        return _run_adhoc(args)
    return _run_batch(args)


if __name__ == "__main__":
    sys.exit(main())
