from __future__ import annotations

# Pure evaluation_only threshold decisions over already-normalized capability
# scores (cosine_similarity / live_probability / manipulation_probability) -
# lives in domain per the same split as face_matching.py and
# document_fields.py: contract-shaped logic, not a model adapter.
#
# "evaluation_only" per docs/M0_CONTRACT_GOVERNANCE_BASELINE.md and
# AGENTS.md's open-decisions list (production auto-approve/reject policy is
# not yet decided) - mirrors the existing replay_attack/camera_injection
# pattern in ai_modules.ekyc.replay_attack, not a new shape.
#
# face_match and passive_liveness return a 3-way "match"/"consider"/"failed"
# decision (app.adapters.analyzer maps this to the ekyc-analysis/1.0
# contract's NO_ADVERSE_SIGNAL/INCONCLUSIVE/ADVERSE_SIGNAL review_signal
# vocabulary), not a bare bool - both have a genuine manual-review band
# between their two thresholds, same as the reference project's
# match/consider/failed DecisionType (C2-App-036's schemas.py). This isn't
# true for every capability: visual_deepfake only has one threshold in both
# projects (a single-frame suspicious/not-suspicious check, not a scored
# band), so it stays binary.


def decide_face_match(
    cosine_similarity: float, match_threshold: float, consider_threshold: float
) -> tuple[str, list[str]]:
    if cosine_similarity >= match_threshold:
        return "match", []
    if cosine_similarity >= consider_threshold:
        return "consider", ["FACE_MATCH_MANUAL_REVIEW_BAND"]
    return "failed", ["FACE_MATCH_BELOW_CONSIDER_THRESHOLD"]


def decide_passive_liveness(
    live_probability: float, threshold: float, consider_threshold: float
) -> tuple[str, list[str]]:
    if live_probability >= threshold:
        return "match", []
    if live_probability >= consider_threshold:
        return "consider", ["LIVENESS_MANUAL_REVIEW_BAND"]
    return "failed", ["LIVENESS_BELOW_CONSIDER_THRESHOLD"]


def decide_visual_deepfake(
    manipulation_probability: float, threshold: float
) -> tuple[bool, list[str]]:
    if manipulation_probability >= threshold:
        return True, ["DEEPFAKE_SUSPICIOUS_SCORE"]
    return False, []
