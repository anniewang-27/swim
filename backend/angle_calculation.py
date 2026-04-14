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


def _angle_debug_info(a: dict | None, b: dict | None, c: dict | None) -> dict:
    missing = []
    low_visibility = []

    for label, pt in (("a", a), ("b", b), ("c", c)):
        if pt is None:
            missing.append(label)
            continue
        if pt.get("visibility", 0) < 0.5:
            low_visibility.append({
                "point": label,
                "name": pt.get("name"),
                "visibility": round(pt.get("visibility", 0), 3),
            })

    return {
        "missing_points": missing,
        "low_visibility_points": low_visibility,
    }


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


def debug_angles_for_frame(keypoints: list[dict]) -> dict:
    """Explain why each angle was or was not available for a frame."""
    debug: dict = {}
    for label, a_name, b_name, c_name in ANGLE_DEFINITIONS:
        a = _get_landmark(keypoints, a_name)
        b = _get_landmark(keypoints, b_name)
        c = _get_landmark(keypoints, c_name)
        angle = _angle_between(a, b, c) if a and b and c else None
        info = _angle_debug_info(a, b, c)
        debug[label] = {
            "angle": angle,
            "required_landmarks": [a_name, b_name, c_name],
            "status": "ok" if angle is not None else "missing_or_low_visibility",
            **info,
        }
    return debug


def calculate_all_angles(pose_results: list[dict]) -> list[dict]:
    """Calculate angles across all frames."""
    return [
        calculate_angles_for_frame(result["keypoints"])
        for result in pose_results
    ]


def debug_all_angles(pose_results: list[dict]) -> list[dict]:
    """Return per-frame debug info for each tracked angle."""
    return [
        {
            "frame": i,
            "detected_keypoints": len(result["keypoints"]),
            "angles": debug_angles_for_frame(result["keypoints"]),
        }
        for i, result in enumerate(pose_results)
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

    def _range(vals):
        return round(max(vals) - min(vals), 4) if len(vals) >= 2 else None

    def _avg_abs_step(vals):
        deltas = [abs(vals[i] - vals[i - 1]) for i in range(1, len(vals))]
        return _avg(deltas), deltas

    def _downward_press(vals):
        if len(vals) < 2:
            return None
        baseline = min(vals)
        return round(max(v - baseline for v in vals), 4)

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

    # Body undulation: track how far head, chest, and hips are pushed DOWN
    # through the stroke. In image coordinates, larger y means lower in frame.
    # Butterfly should show larger synchronized downward press across these parts.
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

    # Frame-to-frame movement still helps, but the main butterfly signal we want is
    # the amplitude of the downward press for head, chest, and hips.
    avg_hip_y_delta, hip_y_deltas = _avg_abs_step(hip_y_values)
    avg_chest_y_delta, chest_y_deltas = _avg_abs_step(chest_y_values)
    avg_head_y_delta, head_y_deltas = _avg_abs_step(head_y_values)

    hip_downward_press = _downward_press(hip_y_values)
    chest_downward_press = _downward_press(chest_y_values)
    head_downward_press = _downward_press(head_y_values)

    down_press_values = [
        v for v in [hip_downward_press, chest_downward_press, head_downward_press]
        if v is not None
    ]
    body_undulation_score = round(sum(down_press_values) / len(down_press_values), 4) if down_press_values else None

    # Butterfly should look like a wave: chest presses down first, then hips follow.
    shared_len = min(len(hip_y_values), len(chest_y_values), len(head_y_values))
    wave_steps = []
    wave_frames = 0
    for i in range(1, shared_len):
        chest_step = chest_y_values[i] - chest_y_values[i - 1]
        head_step = head_y_values[i] - head_y_values[i - 1]
        same_frame_hip_step = hip_y_values[i] - hip_y_values[i - 1]
        next_hip_step = hip_y_values[i + 1] - hip_y_values[i] if i + 1 < shared_len else None

        chest_leads_hip = chest_step > 0 and (
            (next_hip_step is not None and next_hip_step > 0) or same_frame_hip_step > 0
        )
        head_supports_entry = head_step > 0

        step = {
            "frame_pair": [i - 1, i],
            "chest_delta": round(chest_step, 4),
            "head_delta": round(head_step, 4),
            "hip_delta_same_frame": round(same_frame_hip_step, 4),
            "hip_delta_next_frame": round(next_hip_step, 4) if next_hip_step is not None else None,
            "chest_leads_hip": chest_leads_hip,
            "head_supports_entry": head_supports_entry,
            "wave_downward": chest_leads_hip and head_supports_entry,
        }
        wave_steps.append(step)
        if step["wave_downward"]:
            wave_frames += 1

    downward_press_ratio = round(wave_frames / len(wave_steps), 3) if wave_steps else None

    # Classify undulation based on how far the body is pressed downward, not just
    # generic motion. Thresholds are in normalized image coordinates.
    if body_undulation_score is not None:
        if body_undulation_score > 0.08 or (body_undulation_score > 0.05 and (downward_press_ratio or 0) > 0.3):
            undulation_class = "high"  # strong butterfly signal — whole body presses downward
        elif body_undulation_score > 0.04 or (body_undulation_score > 0.025 and (downward_press_ratio or 0) > 0.2):
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
        "hip_y_range": _range(hip_y_values),
        "hip_y_deltas": [round(d, 4) for d in hip_y_deltas],
        "chest_y_values": [round(v, 4) for v in chest_y_values],
        "chest_y_range": _range(chest_y_values),
        "chest_y_deltas": [round(d, 4) for d in chest_y_deltas],
        "head_y_values": [round(v, 4) for v in head_y_values],
        "head_y_range": _range(head_y_values),
        "head_y_deltas": [round(d, 4) for d in head_y_deltas],
        "avg_hip_y_delta": avg_hip_y_delta,
        "avg_chest_y_delta": avg_chest_y_delta,
        "avg_head_y_delta": avg_head_y_delta,
        "hip_downward_press": hip_downward_press,
        "chest_downward_press": chest_downward_press,
        "head_downward_press": head_downward_press,
        "body_undulation_score": body_undulation_score,
        "wave_downward_ratio": downward_press_ratio,
        "wave_downward_steps": wave_steps,
        "undulation_class": undulation_class,
        "kick_pattern": kick_pattern,
        "avg_knee_sync": avg_knee_sync,
    }
