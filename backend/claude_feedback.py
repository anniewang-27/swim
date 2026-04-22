import base64
import json
import os
import time
import logging
import requests
import cv2

logger = logging.getLogger("swim")


def _frame_to_base64(frame) -> str:
    """Encode a BGR numpy frame as a JPEG base64 string."""
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return base64.b64encode(buf).decode("utf-8")


def _gemini_request(api_key: str, parts: list, max_tokens: int = 256) -> str:
    """Send a request to Gemini and return the last text part."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    for attempt in range(3):
        response = requests.post(url, json={
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": max_tokens,
            }
        })

        if response.status_code in (429, 503):
            wait = 3 * (attempt + 1)
            logger.warning(f"Gemini {response.status_code}, retrying in {wait}s (attempt {attempt+1}/3)")
            time.sleep(wait)
            continue

        if not response.ok:
            raise Exception(f"Gemini API error ({response.status_code}): {response.text}")
        break
    else:
        raise Exception("Gemini API rate limit — please wait a minute and try again")

    data = response.json()
    resp_parts = data["candidates"][0]["content"]["parts"]
    response_text = ""
    for part in resp_parts:
        if "text" in part:
            response_text = part["text"]
    return response_text



def get_swim_feedback(
    angles: list[dict],
    pose_results: list[dict],
    frames: list,
    stroke_metrics: dict = None,
) -> dict:
    """
    Send angle data + frame images to Gemini.
    Gemini identifies the stroke itself and provides feedback for that stroke.
    """
    api_key = os.getenv("GEMINI_API_KEY")

    # Build a summary of the angle data across frames
    angle_summary = json.dumps(angles, indent=2, default=str)
    metrics_summary = json.dumps(stroke_metrics, indent=2) if stroke_metrics else "Not available"

    # Don't tell Gemini the user's selection — it biases the detection
    hint_line = "You MUST determine the stroke yourself from the images and angle data. Do NOT guess or assume — use the evidence."

    prompt = f"""You are an expert swim coach analyzing a swimmer's technique from a side-angle video.

I'm providing you with:
1. Frame images from the swim video
2. Joint angle data extracted from those frames (via pose estimation)
3. Aggregate stroke metrics computed from the angle data

{hint_line}

STEP 1: Identify the swimming stroke using BOTH the images AND the angle metrics below.

CRITICAL: Read the metrics carefully. The knee_bend_class and angle data are computed from actual body tracking — trust these numbers over your visual impression of the images.

IMPORTANT: Do NOT default to freestyle just because the swimmer is horizontal and moving forward. Freestyle and backstroke can both have low undulation and alternating kicks. Treat them as a separate decision pair.

=== STROKE IDENTIFICATION RULES (check in this order) ===

CRITICAL DATA-QUALITY RULES:
- If a metric class is "insufficient_data", MediaPipe could not reliably measure that aspect. Do NOT use that metric to classify — fall back to other signals and/or the images.
- If metric signals CONFLICT (e.g. kick_pattern says alternating but knee_bend_class says very_deep), trust the signal that has more multi-frame support. kick_pattern is computed across ALL frames and is more robust than single-frame peak measurements.
- When metrics conflict and images are also ambiguous, prefer "low" confidence or "unknown" over a confident guess.

RULE 1 — PRIMARY signal: kick_pattern
Kick pattern is the most reliable metric because it measures left/right symmetry across many frames.
- "alternating" → the stroke is FREESTYLE or BACKSTROKE (legs move opposite each other in a flutter kick)
- "synchronized" or "mostly_synchronized" → the stroke is BUTTERFLY or BREASTSTROKE (both legs move together)
- "unknown" → insufficient data, fall back to images

RULE 2 — If kick_pattern is "alternating" (freestyle vs backstroke), use BODY ORIENTATION from the images:
- Face UP, torso up → BACKSTROKE
- Face DOWN or rotated side-down → FREESTYLE
- Unclear orientation → "low" confidence, prefer "unknown"
- Knee bend should be "straight" or "moderate" for both. If knee says "very_deep" but kick is alternating, this is MediaPipe noise — IGNORE the knee signal.

RULE 3 — If kick_pattern is "synchronized" (butterfly vs breaststroke), distinguish using knee bend and undulation:
- BREASTSTROKE: knee_bend_class is "very_deep" or "deep" (frog kick pulls knees under the body). Undulation typically lower than butterfly.
- BUTTERFLY: knee_bend_class is "moderate" or "straight" (dolphin kick keeps legs together but fairly straight). undulation_class "high" or "moderate" (body wave).
- If knee is deep AND undulation is clearly high → lean BUTTERFLY with a powerful kick, but this is rare; default to BREASTSTROKE unless images clearly show arms coming OVER the water.
- Images are critical here: breaststroke arms stay underwater; butterfly arms recover over the water.

RULE 4 — Distinguish backstroke from freestyle using visual cues:
- BACKSTROKE signals:
  - the swimmer is face-UP or torso-up in the water
  - the face is visible across many frames
  - the recovering arm passes upward/backward near or over the head/shoulder line
  - recovery often looks relatively straight and vertical
- FREESTYLE signals:
  - the swimmer is face-DOWN or rotated downward toward the water
  - the face is only briefly visible during breaths, or mostly not visible
  - the recovering arm travels forward over the water rather than backward over the head
  - recovery is more side/front-oriented rather than vertical-overhead

RULE 5 — Confidence handling for freestyle vs backstroke:
- If the evidence for face-up vs face-down orientation is weak or conflicting, do NOT guess aggressively.
- If alternating kick + low undulation is clear but orientation is unclear, use "low" confidence.
- If the evidence is too ambiguous to separate freestyle from backstroke, prefer "unknown" over a confident but weak guess.

=== CONFIDENCE CALIBRATION ===
Be HONEST about confidence. Do NOT default to "high".
- "high": Multiple rules clearly point to the same stroke AND the images clearly show the stroke pattern
- "medium": Rules point to one stroke but one important cue is unclear
- "low": Rules conflict with each other, or data is missing/sparse, or you are not sure, especially for freestyle vs backstroke

If the angle metrics are mostly null/None, your confidence should be "medium" at best since you only have images.

Aggregate stroke metrics:
{metrics_summary}

STEP 2: Then analyze technique for the stroke you identified.

Note: The video is filmed from a side angle, so joint angles in the sagittal plane (elbow bend, knee bend, hip flexion) are most reliable. Angles involving depth (rotation, lateral movement) may be less accurate due to the 2D perspective.

Joint angle data per frame (degrees):
{angle_summary}

Analyze BOTH the images and the angle data to provide technique feedback.
Look at body position, head alignment, arm entry, catch position, kick depth,
hip rotation, and overall streamline.

IMPORTANT — Write feedback for a swimmer, NOT a developer:
- Do NOT mention specific degree numbers, frame numbers, or angle measurements in your output.
- Do NOT reference "Frame 3" or "knee angle 142°" or metric names like "hip_downward_press".
- Use plain, descriptive language a swimmer would understand (e.g. "your knees bend too much during the kick" instead of "knee angle of 105°").
- Describe what you observed in human terms: body position, timing, smoothness, power, alignment.

Provide feedback in the following JSON format:
{{
  "detected_stroke": "<freestyle|backstroke|breaststroke|butterfly|unknown>",
  "stroke_confidence": "<high|medium|low>",
  "overall_score": <1-10>,
  "summary": "<2-3 sentence overall assessment in plain language>",
  "issues": [
    {{
      "title": "<short issue name>",
      "severity": "<low|medium|high>",
      "description": "<what you observed, in plain language with no numbers>",
      "suggestion": "<how to fix it, in plain language>",
      "drill": "<a specific drill or exercise to improve this>"
    }}
  ],
  "strengths": ["<thing they're doing well, in plain language>"],
  "dryland_exercises": [
    {{
      "name": "<exercise name>",
      "description": "<how to perform it>",
      "purpose": "<what it improves for swimming>"
    }}
  ]
}}

Return ONLY valid JSON, no other text."""

    # Build multimodal parts: limit to 5 frames to stay within rate limits
    parts = []
    has_keypoints = False  # track if pose data is available

    # Pick up to 5 frames that have keypoints, spread across the video
    valid_indices = [i for i, r in enumerate(pose_results)
                     if r.get("annotated_frame") is not None and len(r.get("keypoints", [])) > 0]
    if len(valid_indices) > 5:
        step = len(valid_indices) / 5
        valid_indices = [valid_indices[int(i * step)] for i in range(5)]

    if valid_indices:
        has_keypoints = True
        for i in valid_indices:
            if i < len(frames):
                b64 = _frame_to_base64(frames[i])
                parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": b64,
                    }
                })
                parts.append({"text": f"[Frame {i} — angles: {json.dumps(angles[i], default=str)}]"})

    # Add the main prompt at the end
    parts.append({"text": prompt})

    logger.info(f"Sending {sum(1 for p in parts if 'inline_data' in p)} images + text to Gemini")

    response_text = _gemini_request(api_key, parts, max_tokens=8192)
    logger.info(f"Raw Gemini feedback (first 500 chars): {response_text[:500]}")

    # Strip markdown code fences if present
    response_text = response_text.strip()
    if "```json" in response_text:
        response_text = response_text.split("```json", 1)[1]
    if "```" in response_text:
        response_text = response_text.split("```")[0]
    response_text = response_text.strip()

    # Also try to extract JSON from anywhere in the text
    if not response_text.startswith("{"):
        start = response_text.find("{")
        if start != -1:
            response_text = response_text[start:]

    logger.info(f"Cleaned response (first 300 chars): {response_text[:300]}")

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {e}")
        result = {
            "overall_score": None,
            "summary": response_text,
            "issues": [],
            "strengths": [],
            "dryland_exercises": [],
        }

    if not has_keypoints:
        result["pose_warning"] = "No body keypoints were detected — feedback is based on visual analysis only and may be less accurate. Try a video with clearer visibility of the swimmer's body."

    return result
