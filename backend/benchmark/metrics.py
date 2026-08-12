from __future__ import annotations

import math
from collections.abc import Sequence


def _edit_distance(a: Sequence, b: Sequence) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i] + [0] * len(b)
        for j, char_b in enumerate(b, start=1):
            cost = 0 if char_a == char_b else 1
            current[j] = min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + cost,
            )
        previous = current
    return previous[-1]


def cer(reference: str, hypothesis: str) -> float:
    """Character error rate: edit distance over reference length."""
    if not reference:
        return 0.0 if not hypothesis else 1.0
    return _edit_distance(reference, hypothesis) / len(reference)


def wer(reference: str, hypothesis: str) -> float:
    """Word error rate: edit distance over reference word count."""
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    return _edit_distance(ref_words, hyp_words) / len(ref_words)


def exact_match(reference: str, hypothesis: str) -> bool:
    return reference == hypothesis


def mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def percentile(values: Sequence[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return ordered[int(k)]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float] | None:
    """95%-style Wilson score interval for a proportion, avoids the normal
    approximation's breakdown near 0/1 that small benchmark sample counts hit."""
    if total == 0:
        return None
    phat = successes / total
    denom = 1 + z * z / total
    center = phat + z * z / (2 * total)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total)
    return max(0.0, (center - margin) / denom), min(1.0, (center + margin) / denom)
