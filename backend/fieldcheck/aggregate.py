from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from benchmark import metrics
from fieldcheck.runner import CaseRunResult

_INFORMATIONAL_SCORING_NOTE = (
    "No capability in this pipeline has an approved decision threshold "
    "(threshold.approval_status is NOT_APPROVED/EVALUATION_ONLY everywhere in "
    "OfflineModelAnalyzer) - these counts are review_signal string matches against "
    'case.json\'s "expected" values, not pass/fail against a governed decision.'
)


def _walk_signals(node: Any, path: str) -> Iterator[tuple[str, dict[str, Any]]]:
    """Recursively find every dict carrying an `execution_status` key (the
    OfflineModelAnalyzer._base_output contract element shared by every
    capability/document/sub-signal), yielding (dotted_path, node). Generic by
    design: walks whatever shape analyze()'s "capabilities" or
    analyze_document()'s "documents" dict actually has, instead of hardcoding
    capability names that could drift from the real contract."""
    if isinstance(node, dict):
        if "execution_status" in node:
            yield path, node
        for key, value in node.items():
            if key == "attempts":  # own status vocabulary, not a signal itself
                continue
            child_path = f"{path}.{key}" if path else key
            yield from _walk_signals(value, child_path)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk_signals(value, f"{path}[{index}]")


def _signal_paths(result: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    root = result.get("capabilities", result.get("documents", {}))
    yield from _walk_signals(root, "")


def _stats(values: list[float]) -> dict[str, Any]:
    return {
        "sample_count": len(values),
        "mean": metrics.mean(values),
        "p50": metrics.percentile(values, 0.5),
        "p95": metrics.percentile(values, 0.95),
    }


def aggregate(results: list[CaseRunResult]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    case_latency_ms: list[float] = []
    per_signal: dict[str, dict[str, Any]] = {}
    latency_by_signal: dict[str, list[float]] = {}
    expected_tally: dict[str, dict[str, int]] = {}

    for run in results:
        status_counts[run.status] = status_counts.get(run.status, 0) + 1
        if run.duration_ms is not None:
            case_latency_ms.append(run.duration_ms)
        if run.status != "RAN" or run.result is None:
            continue

        signals = dict(_signal_paths(run.result))
        for path, node in signals.items():
            bucket = per_signal.setdefault(
                path, {"execution_status": {}, "review_signal": {}, "numeric_metrics": {}}
            )
            exec_status = str(node.get("execution_status"))
            bucket["execution_status"][exec_status] = (
                bucket["execution_status"].get(exec_status, 0) + 1
            )
            review_signal = node.get("review_signal")
            if review_signal is not None:
                bucket["review_signal"][review_signal] = (
                    bucket["review_signal"].get(review_signal, 0) + 1
                )
            for key, value in (node.get("metrics") or {}).items():
                if key == "score_direction" or isinstance(value, bool) or not isinstance(
                    value, (int, float)
                ):
                    continue
                bucket["numeric_metrics"].setdefault(key, []).append(float(value))
            for attempt in node.get("attempts") or []:
                duration = attempt.get("duration_ms")
                if duration is not None:
                    latency_by_signal.setdefault(path, []).append(float(duration))

        for path, expected_signal in run.expected.items():
            tally = expected_tally.setdefault(
                path, {"correct": 0, "incorrect": 0, "no_actual_result": 0}
            )
            actual_node = signals.get(path)
            if actual_node is None:
                tally["no_actual_result"] += 1
                continue
            if actual_node.get("review_signal") == expected_signal:
                tally["correct"] += 1
            else:
                tally["incorrect"] += 1

    signal_report = {
        path: {
            "execution_status": bucket["execution_status"],
            "review_signal": bucket["review_signal"],
            "metrics": {
                key: _stats(values) for key, values in bucket["numeric_metrics"].items()
            },
            "attempt_latency_ms": (
                _stats(latency_by_signal[path]) if path in latency_by_signal else None
            ),
        }
        for path, bucket in per_signal.items()
    }

    return {
        "case_count": len(results),
        "status_counts": status_counts,
        "case_latency_ms": _stats(case_latency_ms) if case_latency_ms else None,
        "signals": signal_report,
        "informational_only_scoring": {
            "note": _INFORMATIONAL_SCORING_NOTE,
            "by_signal": expected_tally,
        },
    }
