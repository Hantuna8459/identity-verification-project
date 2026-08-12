from __future__ import annotations

from typing import Any

from fieldcheck.runner import CaseRunResult


def print_readiness(readiness: dict[str, Any]) -> None:
    print(f"model readiness (profile={readiness['profile']!r}):")
    print(
        f"  manifest present={readiness['manifest']}  artifact_ready={readiness['artifact_ready']}"
    )
    for name, info in readiness.get("capabilities", {}).items():
        if info.get("status") == "NOT_REGISTERED":
            print(f"  {name:20s} NOT_REGISTERED")
            continue
        roles = []
        for role in ("primary", "secondary"):
            role_info = info.get(role)
            if role_info is None:
                continue
            mark = (
                "ready"
                if role_info["ready"]
                else f"NOT READY ({', '.join(role_info['invalid'])})"
            )
            roles.append(f"{role}={role_info['provider_id']}:{mark}")
        print(f"  {name:20s} {' | '.join(roles)}")
    print()


def _format_metrics(metrics: dict[str, Any] | None) -> str:
    if not metrics:
        return ""
    shown = ", ".join(
        f"{key}={value:.3f}" if isinstance(value, float) else f"{key}={value}"
        for key, value in metrics.items()
        if key != "score_direction"
    )
    return f" [{shown}]" if shown else ""


def _print_signal(label: str, node: dict[str, Any], indent: str = "  ") -> None:
    status = node.get("execution_status")
    signal = node.get("review_signal")
    print(f"{indent}{label}: {status} / {signal}{_format_metrics(node.get('metrics'))}")


def print_case_result(result: CaseRunResult) -> None:
    suffix = f" ({result.error})" if result.error else ""
    print(f"case {result.case_id!r}: {result.status}{suffix}")
    if result.status != "RAN" or result.result is None:
        print()
        return

    body = result.result
    if "capabilities" in body:
        print(
            f"  contract={body.get('contract_version')} "
            f"execution_status={body.get('execution_status')}"
        )
        for name, node in body["capabilities"].items():
            documents = node.get("documents") if name == "ocr" else None
            if isinstance(documents, dict):
                print(f"  ocr: {node.get('execution_status')}")
                for doc_name, doc_node in documents.items():
                    _print_signal(f"document[{doc_name}]", doc_node, indent="    ")
                    for sub in ("layout", "mrz_validation"):
                        if isinstance(doc_node.get(sub), dict):
                            _print_signal(sub, doc_node[sub], indent="      ")
                continue
            _print_signal(name, node)
    elif "documents" in body:
        for doc_name, doc_node in body["documents"].items():
            _print_signal(f"document[{doc_name}]", doc_node)
            if isinstance(doc_node.get("mrz_validation"), dict):
                _print_signal("mrz_validation", doc_node["mrz_validation"], indent="    ")
    print()


def print_aggregate(agg: dict[str, Any]) -> None:
    print(f"cases: {agg['case_count']}  status_counts={agg['status_counts']}")
    if agg.get("case_latency_ms"):
        stats = agg["case_latency_ms"]
        print(
            f"case wall-clock latency ms: mean={stats['mean']:.1f} p50={stats['p50']:.1f} "
            f"p95={stats['p95']:.1f} (n={stats['sample_count']})"
        )
    print("per-signal:")
    for path, info in sorted(agg["signals"].items()):
        print(f"  {path}")
        print(f"    execution_status: {info['execution_status']}")
        if info["review_signal"]:
            print(f"    review_signal:    {info['review_signal']}")
        for metric_name, stats in info["metrics"].items():
            print(
                f"    {metric_name}: mean={stats['mean']:.3f} p50={stats['p50']:.3f} "
                f"p95={stats['p95']:.3f} (n={stats['sample_count']})"
            )
        if info["attempt_latency_ms"]:
            stats = info["attempt_latency_ms"]
            print(
                f"    attempt latency ms: mean={stats['mean']:.1f} p50={stats['p50']:.1f} "
                f"p95={stats['p95']:.1f} (n={stats['sample_count']})"
            )

    scoring = agg.get("informational_only_scoring", {})
    if scoring.get("by_signal"):
        print(f"informational-only scoring ({scoring['note']}):")
        for path, tally in scoring["by_signal"].items():
            print(f"  {path}: {tally}")
