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

    for attempt in range(5):
        response = requests.post(url, json={
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": max_tokens,
            }
        })

        if response.status_code in (429, 503):
            wait = 5 * (attempt + 1)
            logger.warning(f"Gemini {response.status_code}, retrying in {wait}s (attempt {attempt+1}/5)")
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


def detect_stroke(frames: list, pose_results: list) -> dict:
    """
    Send ~5 frames from the middle of the video to Gemini to identify the swimming stroke.
    Returns {"detected_stroke": "freestyle", "confidence": "high"}.
    """
    api_key = os.getenv("GEMINI_API_KEY")

    # Pick up to 5 frames from the middle portion of the video (where mid-stroke is likely)
    # Avoid the first and last 20% of frames (often diving, turns, or finishing)
    n = len(frames)
    start_idx = max(0, n // 5)
    end_idx = min(n, n - n // 5)
    middle_frames = list(range(start_idx, end_idx))

    # From the middle portion, pick frames that have keypoints
    selected = []
    for i in middle_frames:
        if i < len(pose_results) and len(pose_results[i].get("keypoints", [])) > 0:
            selected.append(i)
        if len(selected) >= 5:
            break

    # Fallback: if not enough from middle, try all frames
    if len(selected) < 2:
        for i, result in enumerate(pose_results):
            if i not in selected and len(result.get("keypoints", [])) > 0:
                selected.append(i)
            if len(selected) >= 5:
                break

    if not selected:
        return {"detected_stroke": "unknown", "confidence": "low"}

    # Send original frames (without skeleton overlay) for cleaner visual recognition
    parts = []
    for i in selected:
        b64 = _frame_to_base64(frames[i])
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": b64,
            }
        })

    parts.append({"text": """These are frames from a swimming video filmed from the side angle.
Identify the swimming stroke being performed by looking at the arm movement pattern, kick style, and body position.

Key differences:
- Freestyle (front crawl): alternating overarm strokes, flutter kick, face in water with side breathing
- Backstroke: on back, alternating arm rotation, flutter kick
- Breaststroke: simultaneous arm sweep outward, frog/whip kick, body rises and dips
- Butterfly: simultaneous overarm recovery, dolphin kick, undulating body motion

Return ONLY a JSON object in this exact format, no other text:
{"detected_stroke": "<freestyle|backstroke|breaststroke|butterfly|unknown>", "confidence": "<high|medium|low>"}"""})

    logger.info(f"Detecting stroke from {len(selected)} frames (indices: {selected})...")
    response_text = _gemini_request(api_key, parts)
    logger.info(f"Stroke detection response: {response_text[:200]}")

    # Parse response
    response_text = response_text.strip()
    if "```" in response_text:
        response_text = response_text.split("```json")[-1].split("```")[0].strip()
    if not response_text.startswith("{"):
        start = response_text.find("{")
        if start != -1:
            response_text = response_text[start:]

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        return {"detected_stroke": "unknown", "confidence": "low"}


def get_swim_feedback(
    angles: list[dict],
    pose_results: list[dict],
    frames: list,
    stroke_hint: str = "",
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
1. Annotated frame images from the swim video (with pose skeleton overlay)
2. Original (clean) frame images for visual reference
3. Joint angle data extracted from those frames
4. Aggregate stroke metrics computed from the angle data

{hint_line}

STEP 1: Identify the swimming stroke using BOTH the images AND the angle metrics below.

Stroke identification guide using angle metrics:
- **Freestyle (front crawl)**: High left/right arm asymmetry (avg_left_right_elbow_diff > 15°, avg_left_right_shoulder_diff > 15°) because arms alternate. Moderate knee angles (140-170°) with flutter kick. Body is face-down.
- **Backstroke**: High left/right arm asymmetry (alternating arms). Body is face-up (look at the images). Flutter kick with moderate knee angles.
- **Breaststroke**: Low left/right asymmetry (arms and legs move together). Very deep knee bend (min_knee_angle < 100°). High knee_angle_variance as legs go from tucked to extended. Arms stay underwater.
- **Butterfly**: Low left/right asymmetry (both arms move together). High hip_angle_variance (undulating body motion). Both arms recover over the water simultaneously. Dolphin kick with moderate knee angles.

Key distinguishing factors:
- Symmetrical arms + deep knee bend = BREASTSTROKE
- Symmetrical arms + high hip variance + arms over water = BUTTERFLY
- Alternating arms + face down = FREESTYLE
- Alternating arms + face up = BACKSTROKE

Aggregate stroke metrics:
{metrics_summary}

STEP 2: Then analyze technique for the stroke you identified.

Note: The video is filmed from a side angle, so joint angles in the sagittal plane (elbow bend, knee bend, hip flexion) are most reliable. Angles involving depth (rotation, lateral movement) may be less accurate due to the 2D perspective.

Joint angle data per frame (degrees):
{angle_summary}

Analyze BOTH the images and the angle data to provide technique feedback.
Look at body position, head alignment, arm entry, catch position, kick depth,
hip rotation, and overall streamline.

Provide feedback in the following JSON format:
{{
  "detected_stroke": "<freestyle|backstroke|breaststroke|butterfly|unknown>",
  "stroke_confidence": "<high|medium|low>",
  "overall_score": <1-10>,
  "summary": "<2-3 sentence overall assessment>",
  "issues": [
    {{
      "title": "<short issue name>",
      "severity": "<low|medium|high>",
      "description": "<what you observed>",
      "suggestion": "<how to fix it>",
      "drill": "<a specific drill or exercise to improve this>"
    }}
  ],
  "strengths": ["<thing they're doing well>"],
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

    # Pick up to 5 frames that have keypoints, spread across the video
    valid_indices = [i for i, r in enumerate(pose_results)
                     if r.get("annotated_frame") is not None and len(r.get("keypoints", [])) > 0]
    if len(valid_indices) > 5:
        step = len(valid_indices) / 5
        valid_indices = [valid_indices[int(i * step)] for i in range(5)]

    for i in valid_indices:
        # Original frame for stroke identification
        if i < len(frames):
            b64_orig = _frame_to_base64(frames[i])
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": b64_orig,
                }
            })
        # Annotated frame for technique analysis
        b64_ann = _frame_to_base64(pose_results[i]["annotated_frame"])
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": b64_ann,
            }
        })
        parts.append({"text": f"[Frame {i} — original + annotated — angles: {json.dumps(angles[i], default=str)}]"})

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
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {e}")
        return {
            "overall_score": None,
            "summary": response_text,
            "issues": [],
            "strengths": [],
            "dryland_exercises": [],
        }
