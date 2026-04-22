from __future__ import annotations

import math

# Raised from 0.5 → 0.7 because low-confidence keypoints on underwater/low-contrast
# swim footage cause wild angle swings (e.g. a "58° knee" from a misplaced landmark
# that flips the whole classification to breaststroke). 0.7 trades some recall for
# much higher precision on the kept measurements.
MIN_VISIBILITY = 0.7


def _angle_between(a: dict, b: dict, c: dict) -> float | None:
    """
    Calculate the angle at point b formed by points a-b-c.
    Each point is a keypoint dict with 'x', 'y' keys.
    Returns degrees, or None if any point has low visibility.
    """
    for pt in (a, b, c):
        if pt.get("visibility", 0) < MIN_VISIBILITY:
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
        if pt.get("visibility", 0) < MIN_VISIBILITY:
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

    def _percentile(vals, p):
        """Return the p-th percentile (0-100). More robust than min/max to outliers."""
        if not vals:
            return None
        s = sorted(vals)
        idx = int(round((p / 100) * (len(s) - 1)))
        return s[max(0, min(idx, len(s) - 1))]

    def _filter_outliers(vals, max_step=0.15):
        """Drop values that jump more than max_step from the previous value.
        Used to suppress MediaPipe keypoint jitter on single bad frames."""
        if len(vals) < 2:
            return vals
        cleaned = [vals[0]]
        for v in vals[1:]:
            if abs(v - cleaned[-1]) <= max_step:
                cleaned.append(v)
        return cleaned

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

    # Minimum samples needed before we trust a classification. Below this,
    # MediaPipe has given us so few data points that any percentile is
    # essentially one value, which makes classification brittle.
    MIN_KNEE_SAMPLES = 6

    avg_knee = _avg(all_knee)
    min_knee = round(min(all_knee), 1) if all_knee else None
    p10_knee = round(_percentile(all_knee, 10), 1) if all_knee else None
    median_knee = round(_percentile(all_knee, 50), 1) if all_knee else None

    # Use MEDIAN for classification when sample size is small. Median requires
    # multiple frames to show deep bend before flipping the class, so a single
    # misplaced landmark can't fool us into calling backstroke "breaststroke".
    # With enough samples, p10 is better because it catches brief peak bends
    # that are real (e.g. the breaststroke recovery phase).
    if len(all_knee) >= MIN_KNEE_SAMPLES:
        knee_bend_reference = p10_knee
    else:
        knee_bend_reference = median_knee

    # Require BOTH p10 and median to indicate a deep bend before classifying very_deep.
    # This prevents a few misplaced frames from triggering breaststroke when the
    # bulk of frames show a straight/moderate leg (backstroke or freestyle).
    if avg_knee is not None and knee_bend_reference is not None and len(all_knee) >= 4:
        if knee_bend_reference < 70 and (median_knee or 999) < 110:
            knee_bend_class = "very_deep"  # strong breaststroke signal — must be confirmed by median
        elif knee_bend_reference < 110 and (median_knee or 999) < 135:
            knee_bend_class = "deep"  # breaststroke or butterfly
        elif knee_bend_reference < 140:
            knee_bend_class = "moderate"  # could be any stroke
        else:
            knee_bend_class = "straight"  # freestyle or backstroke flutter kick
    else:
        knee_bend_class = "insufficient_data"

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

    # Remove frame-to-frame outliers before measuring undulation. A swimmer's hip
    # cannot physically teleport 8% of the frame height between adjacent frames
    # on any reasonable framerate — those jumps are MediaPipe jitter, not real
    # motion. Tightening the threshold from 0.15 → 0.08 suppresses the jitter
    # that was inflating the "undulation" score on shaky backstroke footage.
    hip_y_values = _filter_outliers(hip_y_values, max_step=0.08)
    chest_y_values = _filter_outliers(chest_y_values, max_step=0.08)
    head_y_values = _filter_outliers(head_y_values, max_step=0.08)

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

    # Require a minimum of 4 valid hip y-values (post-outlier-filter) before
    # classifying undulation. Otherwise we're classifying off noise.
    MIN_UNDULATION_SAMPLES = 4
    has_enough_y_data = (
        len(hip_y_values) >= MIN_UNDULATION_SAMPLES
        and len(chest_y_values) >= MIN_UNDULATION_SAMPLES
    )

    # Classify undulation. Thresholds are in normalized image coordinates.
    # Raised significantly because MediaPipe jitter on low-quality footage was
    # producing fake "high" undulation scores (~0.1-0.22) on freestyle/backstroke
    # videos where the body should be flat. True butterfly shows downward press
    # ratio that climbs alongside the score.
    if body_undulation_score is not None and has_enough_y_data:
        if body_undulation_score > 0.18 and (downward_press_ratio or 0) > 0.35:
            undulation_class = "high"  # strong butterfly signal — whole body presses downward in a wave
        elif body_undulation_score > 0.10 and (downward_press_ratio or 0) > 0.25:
            undulation_class = "moderate"  # possible butterfly
        else:
            undulation_class = "low"  # freestyle or backstroke — body stays flat
    elif body_undulation_score is not None:
        undulation_class = "insufficient_data"
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
        "p10_knee_angle": p10_knee,  # what the classifier uses — robust to single outlier frames
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
