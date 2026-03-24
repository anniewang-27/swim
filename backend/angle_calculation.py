from __future__ import annotations

import math


def _angle_between(a: dict, b: dict, c: dict) -> float | None:
    """
    Calculate the angle at point b formed by points a-b-c.
    Each point is a keypoint dict with 'x', 'y' keys.
    Returns degrees, or None if any point has low visibility.
    """
    for pt in (a, b, c):
        if pt.get("visibility", 0) < 0.5:
            return None

    ba = (a["x"] - b["x"], a["y"] - b["y"])
    bc = (c["x"] - b["x"], c["y"] - b["y"])

    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.hypot(*ba)
    mag_bc = math.hypot(*bc)

    if mag_ba == 0 or mag_bc == 0:
        return None

    cos_angle = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_angle))


def _get_landmark(keypoints: list[dict], name: str) -> dict | None:
    for kp in keypoints:
        if kp["name"] == name:
            return kp
    return None


# Angles we care about for swim analysis
ANGLE_DEFINITIONS = [
    ("left_elbow", "LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST"),
    ("right_elbow", "RIGHT_SHOULDER", "RIGHT_ELBOW", "RIGHT_WRIST"),
    ("left_shoulder", "LEFT_HIP", "LEFT_SHOULDER", "LEFT_ELBOW"),
    ("right_shoulder", "RIGHT_HIP", "RIGHT_SHOULDER", "RIGHT_ELBOW"),
    ("left_hip", "LEFT_SHOULDER", "LEFT_HIP", "LEFT_KNEE"),
    ("right_hip", "RIGHT_SHOULDER", "RIGHT_HIP", "RIGHT_KNEE"),
    ("left_knee", "LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE"),
    ("right_knee", "RIGHT_HIP", "RIGHT_KNEE", "RIGHT_ANKLE"),
]


def calculate_angles_for_frame(keypoints: list[dict]) -> dict:
    """Calculate all relevant joint angles for a single frame's keypoints."""
    angles: dict = {}
    for label, a_name, b_name, c_name in ANGLE_DEFINITIONS:
        a = _get_landmark(keypoints, a_name)
        b = _get_landmark(keypoints, b_name)
        c = _get_landmark(keypoints, c_name)
        if a and b and c:
            angles[label] = _angle_between(a, b, c)
    return angles


def calculate_all_angles(pose_results: list[dict]) -> list[dict]:
    """Calculate angles across all frames."""
    return [
        calculate_angles_for_frame(result["keypoints"])
        for result in pose_results
    ]
