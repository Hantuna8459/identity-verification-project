from __future__ import annotations

from typing import Any

import numpy as np

from ai_modules.ekyc.errors import InvalidEvidenceError


def estimate_head_yaw(landmarks: np.ndarray) -> float:
    """Estimate horizontal pose from SCRFD five-point landmarks."""
    points = np.asarray(landmarks, dtype=np.float32).reshape(5, 2)
    eye_distance = float(abs(points[1, 0] - points[0, 0]))
    if eye_distance <= 1e-6:
        raise InvalidEvidenceError("Face landmarks cannot estimate head pose")
    eye_center_x = float((points[0, 0] + points[1, 0]) / 2)
    return float((points[2, 0] - eye_center_x) / eye_distance)


def inspect_head_turn_sequence(yaw_samples: list[float]) -> dict[str, Any]:
    """Require center, opposite turns, then center without storing pose samples."""
    center_threshold = 0.08
    turn_threshold = 0.14
    phase = "initial_center"
    first_direction = 0
    completed_steps: list[str] = []

    for yaw in yaw_samples:
        centered = abs(yaw) <= center_threshold
        direction = -1 if yaw <= -turn_threshold else 1 if yaw >= turn_threshold else 0
        if phase == "initial_center" and centered:
            completed_steps.append("INITIAL_CENTER")
            phase = "first_turn"
        elif phase == "first_turn" and direction:
            first_direction = direction
            completed_steps.append("FIRST_TURN")
            phase = "center_between_turns"
        elif phase == "center_between_turns" and centered:
            completed_steps.append("CENTER_BETWEEN_TURNS")
            phase = "opposite_turn"
        elif phase == "opposite_turn" and direction == -first_direction:
            completed_steps.append("OPPOSITE_TURN")
            phase = "final_center"
        elif phase == "final_center" and centered:
            completed_steps.append("FINAL_CENTER")
            phase = "complete"
            break

    complete = phase == "complete"
    return {
        "status": "OK" if complete else "INCONCLUSIVE",
        "engine": "scrfd-5-point-head-pose-rules-v1",
        "sequence_complete": complete,
        "completed_step_count": len(completed_steps),
        "required_step_count": 5,
        "sampled_pose_count": len(yaw_samples),
        **({"reason": "CHALLENGE_SEQUENCE_INCOMPLETE"} if not complete else {}),
    }
