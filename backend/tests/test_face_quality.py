from __future__ import annotations

import numpy as np

from ai_modules.ekyc.face_quality import aggregate_face_quality, assess_face_frame, estimate_roll


def _good_frame(**overrides: object) -> dict[str, object]:
    frame = {
        "blur_score": 200.0,
        "coverage_ratio": 0.2,
        "in_frame": True,
        "face_count": 1,
        "yaw": 0.0,
        "roll": 0.0,
    }
    frame.update(overrides)
    return frame


def test_assess_face_frame_reports_sane_metrics_for_a_centered_face() -> None:
    image = (np.random.default_rng(0).random((300, 300, 3)) * 255).astype(np.uint8)
    bbox = np.array([100.0, 80.0, 200.0, 220.0])
    landmarks = np.array([[130.0, 130.0], [170.0, 130.0], [150.0, 160.0], [135.0, 190.0], [165.0, 190.0]])

    result = assess_face_frame(image, bbox, landmarks, face_count=1)

    assert result["face_count"] == 1
    assert result["in_frame"] is True
    assert 0.0 < result["coverage_ratio"] < 1.0
    assert result["blur_score"] >= 0.0


def test_assess_face_frame_flags_bbox_exceeding_image_bounds() -> None:
    image = np.zeros((200, 200, 3), dtype=np.uint8)
    bbox = np.array([-10.0, 0.0, 100.0, 100.0])
    landmarks = np.array([[30.0, 30.0], [70.0, 30.0], [50.0, 50.0], [35.0, 70.0], [65.0, 70.0]])

    result = assess_face_frame(image, bbox, landmarks, face_count=1)

    assert result["in_frame"] is False


def test_estimate_roll_is_zero_for_level_eyes() -> None:
    landmarks = np.array([[30.0, 50.0], [70.0, 50.0], [50.0, 60.0], [35.0, 80.0], [65.0, 80.0]])

    assert estimate_roll(landmarks) == 0.0


def test_estimate_roll_nonzero_for_tilted_eyes() -> None:
    landmarks = np.array([[30.0, 60.0], [70.0, 40.0], [50.0, 60.0], [35.0, 80.0], [65.0, 80.0]])

    assert estimate_roll(landmarks) != 0.0


def test_aggregate_face_quality_ok_for_clean_frontal_frames() -> None:
    frames = [_good_frame() for _ in range(10)]

    result = aggregate_face_quality(frames, min_video_face_frames=8)

    assert result["status"] == "OK"
    assert result["defect_flags"] == []
    assert result["frontal_frame_found"] is True


def test_aggregate_face_quality_flags_insufficient_frames() -> None:
    frames = [_good_frame() for _ in range(3)]

    result = aggregate_face_quality(frames, min_video_face_frames=8)

    assert "insufficient_face_frames" in result["defect_flags"]
    assert "INSUFFICIENT_FACE_FRAMES" in result["reason_codes"]


def test_aggregate_face_quality_flags_any_multi_face_frame() -> None:
    frames = [_good_frame() for _ in range(9)] + [_good_frame(face_count=2)]

    result = aggregate_face_quality(frames, min_video_face_frames=8)

    assert "multiple_faces_detected" in result["defect_flags"]
    assert result["multi_face_frame_count"] == 1


def test_aggregate_face_quality_tolerates_one_off_blurry_frame() -> None:
    frames = [_good_frame() for _ in range(9)] + [_good_frame(blur_score=5.0)]

    result = aggregate_face_quality(frames, min_video_face_frames=8, blur_threshold=60.0)

    assert "face_blurry" not in result["defect_flags"]


def test_aggregate_face_quality_flags_mostly_blurry_video() -> None:
    frames = [_good_frame(blur_score=5.0) for _ in range(7)] + [_good_frame() for _ in range(3)]

    result = aggregate_face_quality(frames, min_video_face_frames=8, blur_threshold=60.0)

    assert "face_blurry" in result["defect_flags"]
    assert "FACE_BLURRY" in result["reason_codes"]


def test_aggregate_face_quality_flags_mostly_small_face() -> None:
    frames = [_good_frame(coverage_ratio=0.02) for _ in range(7)] + [_good_frame() for _ in range(3)]

    result = aggregate_face_quality(frames, min_video_face_frames=8, min_coverage=0.08)

    assert "face_too_small" in result["defect_flags"]
    assert "FACE_TOO_SMALL" in result["reason_codes"]


def test_aggregate_face_quality_flags_mostly_out_of_frame() -> None:
    frames = [_good_frame(in_frame=False) for _ in range(7)] + [_good_frame() for _ in range(3)]

    result = aggregate_face_quality(frames, min_video_face_frames=8)

    assert "face_out_of_frame" in result["defect_flags"]
    assert "FACE_OUT_OF_FRAME" in result["reason_codes"]


def test_aggregate_face_quality_flags_no_frontal_frame() -> None:
    frames = [_good_frame(yaw=0.3, roll=0.0) for _ in range(10)]

    result = aggregate_face_quality(frames, min_video_face_frames=8, yaw_threshold=0.08)

    assert result["frontal_frame_found"] is False
    assert "no_frontal_frame" in result["defect_flags"]
    assert "NO_FRONTAL_FRAME_FOUND" in result["reason_codes"]


def test_aggregate_face_quality_handles_empty_frame_list() -> None:
    result = aggregate_face_quality([], min_video_face_frames=8)

    assert result["status"] == "DEFECT_DETECTED"
    assert "insufficient_face_frames" in result["defect_flags"]
    assert "no_frontal_frame" not in result["defect_flags"]
