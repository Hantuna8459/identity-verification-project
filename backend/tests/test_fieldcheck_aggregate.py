from __future__ import annotations

from typing import Any

from fieldcheck.aggregate import aggregate
from fieldcheck.runner import CaseRunResult


def _capabilities_result(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "capabilities": {
            "face_match": {
                "execution_status": "COMPLETED",
                "review_signal": "SCORE_AVAILABLE",
                "metrics": {"cosine_similarity": 0.8, "score_direction": "HIGHER_IS_MORE_SIMILAR"},
                "attempts": [{"duration_ms": 120}],
            },
            "liveness": {
                "execution_status": "COMPLETED",
                "review_signal": "SCORE_AVAILABLE",
                "metrics": {"live_probability": 0.9},
                "attempts": [{"duration_ms": 80}],
            },
        }
    }
    base.update(overrides)
    return base


def _face_match(**fields: Any) -> dict[str, Any]:
    return {"capabilities": {"face_match": fields}}


def test_aggregate_counts_status_and_review_signal() -> None:
    results = [
        CaseRunResult(case_id="a", status="RAN", result=_capabilities_result()),
        CaseRunResult(
            case_id="b",
            status="RAN",
            result=_face_match(execution_status="UNAVAILABLE", review_signal="UNAVAILABLE"),
        ),
        CaseRunResult(case_id="c", status="LOAD_FAILED", error="boom"),
    ]

    summary = aggregate(results)

    assert summary["case_count"] == 3
    assert summary["status_counts"] == {"RAN": 2, "LOAD_FAILED": 1}
    face_match = summary["signals"]["face_match"]
    assert face_match["execution_status"] == {"COMPLETED": 1, "UNAVAILABLE": 1}
    assert face_match["review_signal"] == {"SCORE_AVAILABLE": 1, "UNAVAILABLE": 1}


def test_aggregate_computes_numeric_metric_stats() -> None:
    results = [
        CaseRunResult(
            case_id="a",
            status="RAN",
            result=_face_match(execution_status="COMPLETED", metrics={"cosine_similarity": 0.6}),
        ),
        CaseRunResult(
            case_id="b",
            status="RAN",
            result=_face_match(execution_status="COMPLETED", metrics={"cosine_similarity": 0.8}),
        ),
    ]

    summary = aggregate(results)

    stats = summary["signals"]["face_match"]["metrics"]["cosine_similarity"]
    assert stats["sample_count"] == 2
    assert stats["mean"] == 0.7


def test_aggregate_computes_attempt_latency() -> None:
    results = [
        CaseRunResult(
            case_id="a",
            status="RAN",
            result={
                "capabilities": {
                    "liveness": {
                        "execution_status": "COMPLETED",
                        "attempts": [{"duration_ms": 100}, {"duration_ms": 200}],
                    }
                }
            },
        )
    ]

    summary = aggregate(results)

    latency = summary["signals"]["liveness"]["attempt_latency_ms"]
    assert latency is not None
    assert latency["sample_count"] == 2
    assert latency["mean"] == 150


def test_aggregate_nested_ocr_documents_get_their_own_signal_path() -> None:
    results = [
        CaseRunResult(
            case_id="a",
            status="RAN",
            result={
                "capabilities": {
                    "ocr": {
                        "execution_status": "COMPLETED",
                        "documents": {
                            "document_front": {
                                "execution_status": "COMPLETED",
                                "mrz_validation": {"execution_status": "COMPLETED"},
                            }
                        },
                    }
                }
            },
        )
    ]

    summary = aggregate(results)

    assert "ocr" in summary["signals"]
    assert "ocr.documents.document_front" in summary["signals"]
    assert "ocr.documents.document_front.mrz_validation" in summary["signals"]


def test_aggregate_informational_scoring_tallies_expected_vs_actual() -> None:
    results = [
        CaseRunResult(
            case_id="a",
            status="RAN",
            result=_face_match(execution_status="COMPLETED", review_signal="SCORE_AVAILABLE"),
            expected={"face_match": "SCORE_AVAILABLE"},
        ),
        CaseRunResult(
            case_id="b",
            status="RAN",
            result=_face_match(execution_status="UNAVAILABLE", review_signal="UNAVAILABLE"),
            expected={"face_match": "SCORE_AVAILABLE"},
        ),
        CaseRunResult(
            case_id="c",
            status="RAN",
            result={"capabilities": {}},
            expected={"face_match": "SCORE_AVAILABLE"},
        ),
    ]

    summary = aggregate(results)

    tally = summary["informational_only_scoring"]["by_signal"]["face_match"]
    assert tally == {"correct": 1, "incorrect": 1, "no_actual_result": 1}


def test_aggregate_case_latency_stats() -> None:
    results = [
        CaseRunResult(case_id="a", status="RAN", result={"capabilities": {}}, duration_ms=100.0),
        CaseRunResult(case_id="b", status="RAN", result={"capabilities": {}}, duration_ms=300.0),
    ]

    summary = aggregate(results)

    assert summary["case_latency_ms"] is not None
    assert summary["case_latency_ms"]["mean"] == 200.0


def test_aggregate_empty_results() -> None:
    summary = aggregate([])

    assert summary["case_count"] == 0
    assert summary["status_counts"] == {}
    assert summary["case_latency_ms"] is None
    assert summary["signals"] == {}
