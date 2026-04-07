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


def compute_stroke_metrics(angles: list[dict], pose_results: list[dict] = None) -> dict:
    """
    Compute aggregate metrics from angle data across frames that help
    distinguish between swimming strokes.
    """
    def _vals(key):
        return [a[key] for a in angles if a.get(key) is not None]

    def _avg(vals):
        return round(sum(vals) / len(vals), 1) if vals else None

    def _variance(vals):
        if len(vals) < 2:
            return None
        mean = sum(vals) / len(vals)
        return round(sum((v - mean) ** 2 for v in vals) / len(vals), 1)

    left_knee = _vals("left_knee")
    right_knee = _vals("right_knee")
    left_hip = _vals("left_hip")
    right_hip = _vals("right_hip")
    left_elbow = _vals("left_elbow")
    right_elbow = _vals("right_elbow")
    left_shoulder = _vals("left_shoulder")
    right_shoulder = _vals("right_shoulder")

    # Symmetry: how similar are left/right sides frame by frame?
    # Low difference = symmetrical movement (butterfly, breaststroke)
    # High difference = alternating movement (freestyle, backstroke)
    knee_diffs = []
    for a in angles:
        lk = a.get("left_knee")
        rk = a.get("right_knee")
        if lk is not None and rk is not None:
            knee_diffs.append(abs(lk - rk))

    elbow_diffs = []
    for a in angles:
        le = a.get("left_elbow")
        re = a.get("right_elbow")
        if le is not None and re is not None:
            elbow_diffs.append(abs(le - re))

    shoulder_diffs = []
    for a in angles:
        ls = a.get("left_shoulder")
        rs = a.get("right_shoulder")
        if ls is not None and rs is not None:
            shoulder_diffs.append(abs(ls - rs))

    all_knee = left_knee + right_knee
    knee_range = (round(max(all_knee) - min(all_knee), 1)) if len(all_knee) >= 2 else None

    # Classify knee bend pattern
    avg_knee = _avg(all_knee)
    min_knee = round(min(all_knee), 1) if all_knee else None
    if avg_knee is not None and min_knee is not None:
        if min_knee < 90:
            knee_bend_class = "very_deep"  # strong breaststroke signal
        elif min_knee < 120:
            knee_bend_class = "deep"  # breaststroke or butterfly
        elif min_knee < 150:
            knee_bend_class = "moderate"  # could be any stroke
        else:
            knee_bend_class = "straight"  # freestyle or backstroke flutter kick
    else:
        knee_bend_class = "unknown"

    # Body undulation: track vertical (y) position of hips, chest, and head across frames
    # Butterfly: entire body undulates like a wave (hips, chest, head all move up/down)
    # Freestyle: body stays flat and stable in the y axis
    hip_y_values = []
    chest_y_values = []
    head_y_values = []
    if pose_results:
        for result in pose_results:
            kps = result.get("keypoints", [])
            left_hip_kp = _get_landmark(kps, "LEFT_HIP")
            right_hip_kp = _get_landmark(kps, "RIGHT_HIP")
            left_shoulder_kp = _get_landmark(kps, "LEFT_SHOULDER")
            right_shoulder_kp = _get_landmark(kps, "RIGHT_SHOULDER")
            nose_kp = _get_landmark(kps, "NOSE")
            if left_hip_kp and right_hip_kp:
                hip_y_values.append((left_hip_kp["y"] + right_hip_kp["y"]) / 2)
            if left_shoulder_kp and right_shoulder_kp:
                chest_y_values.append((left_shoulder_kp["y"] + right_shoulder_kp["y"]) / 2)
            if nose_kp:
                head_y_values.append(nose_kp["y"])

    # Frame-to-frame vertical movement for each body part
    hip_y_deltas = [abs(hip_y_values[i] - hip_y_values[i - 1]) for i in range(1, len(hip_y_values))]
    chest_y_deltas = [abs(chest_y_values[i] - chest_y_values[i - 1]) for i in range(1, len(chest_y_values))]
    head_y_deltas = [abs(head_y_values[i] - head_y_values[i - 1]) for i in range(1, len(head_y_values))]

    avg_hip_y_delta = _avg(hip_y_deltas)
    avg_chest_y_delta = _avg(chest_y_deltas)
    avg_head_y_delta = _avg(head_y_deltas)

    # Combined undulation score: average vertical movement across all tracked body parts
    # Butterfly moves the whole body; freestyle keeps everything stable
    all_deltas = [d for d in [avg_hip_y_delta, avg_chest_y_delta, avg_head_y_delta] if d is not None]
    body_undulation_score = _avg(all_deltas)

    # Classify undulation based on whole-body movement
    if body_undulation_score is not None:
        if body_undulation_score > 0.025:
            undulation_class = "high"  # strong butterfly signal — whole body waves
        elif body_undulation_score > 0.012:
            undulation_class = "moderate"  # possible butterfly
        else:
            undulation_class = "low"  # freestyle or backstroke — body stays flat
    else:
        undulation_class = "unknown"

    # Knee synchronization: are both knees bending together (butterfly/breaststroke)
    # or alternating (freestyle/backstroke)?
    # Compute correlation-like metric: low diff = synchronized, high diff = alternating
    knee_sync_scores = []
    for a in angles:
        lk = a.get("left_knee")
        rk = a.get("right_knee")
        if lk is not None and rk is not None:
            # Normalized difference: 0 = perfectly synced, 1 = very different
            max_val = max(lk, rk)
            if max_val > 0:
                knee_sync_scores.append(abs(lk - rk) / max_val)
    avg_knee_sync = _avg(knee_sync_scores)
    if avg_knee_sync is not None:
        if avg_knee_sync < 0.05:
            kick_pattern = "synchronized"  # butterfly or breaststroke
        elif avg_knee_sync < 0.15:
            kick_pattern = "mostly_synchronized"
        else:
            kick_pattern = "alternating"  # freestyle or backstroke
    else:
        kick_pattern = "unknown"

    return {
        "avg_knee_angle": avg_knee,
        "knee_angle_variance": _variance(all_knee),
        "knee_angle_range": knee_range,
        "knee_bend_class": knee_bend_class,
        "min_knee_angle": min_knee,
        "max_knee_angle": round(max(all_knee), 1) if all_knee else None,
        "avg_hip_angle": _avg(left_hip + right_hip),
        "hip_angle_variance": _variance(left_hip + right_hip),
        "avg_elbow_angle": _avg(left_elbow + right_elbow),
        "elbow_angle_variance": _variance(left_elbow + right_elbow),
        "avg_shoulder_angle": _avg(left_shoulder + right_shoulder),
        "avg_left_right_knee_diff": _avg(knee_diffs),
        "avg_left_right_elbow_diff": _avg(elbow_diffs),
        "avg_left_right_shoulder_diff": _avg(shoulder_diffs),
        "hip_y_values": [round(v, 4) for v in hip_y_values],
        "hip_y_deltas": [round(d, 4) for d in hip_y_deltas],
        "chest_y_values": [round(v, 4) for v in chest_y_values],
        "chest_y_deltas": [round(d, 4) for d in chest_y_deltas],
        "head_y_values": [round(v, 4) for v in head_y_values],
        "head_y_deltas": [round(d, 4) for d in head_y_deltas],
        "avg_hip_y_delta": avg_hip_y_delta,
        "avg_chest_y_delta": avg_chest_y_delta,
        "avg_head_y_delta": avg_head_y_delta,
        "body_undulation_score": body_undulation_score,
        "undulation_class": undulation_class,
        "kick_pattern": kick_pattern,
        "avg_knee_sync": avg_knee_sync,
    }
