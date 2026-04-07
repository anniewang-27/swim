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

=== STROKE IDENTIFICATION RULES (check in this order) ===

RULE 1 — Check body orientation in the images:
- Is the swimmer face-UP (on their back)? → BACKSTROKE. Stop here.
- Is the swimmer face-DOWN or sideways? → Continue to Rule 2.

RULE 2 — Check knee bend (from knee_bend_class metric):
- "very_deep" or "deep" (min_knee_angle < 120°) with HIGH knee_angle_variance → BREASTSTROKE (frog kick causes extreme knee bend that no other stroke has)
- "straight" or "moderate" (min_knee_angle > 140°) → this is a flutter kick or dolphin kick → continue to Rule 3
- Between 120-140° → ambiguous, continue to Rule 3

RULE 3 — Check whole-body undulation (from undulation_class and body_undulation_score):
- body_undulation_score measures average vertical movement of hips, chest, AND head across frames.
- "high" undulation (score > 0.025) → strong BUTTERFLY signal. In butterfly, the ENTIRE body moves up and down like a worm — hips, chest, and head all undulate through the water.
- "low" undulation (score < 0.012) → FREESTYLE. In freestyle, the body stays flat and stable in the y-axis with minimal vertical movement.
- Also check kick_pattern: "synchronized" = both legs kick together (BUTTERFLY dolphin kick), "alternating" = legs alternate (FREESTYLE flutter kick)
- Check individual parts: if avg_chest_y_delta AND avg_hip_y_delta are both elevated, the whole body is undulating → BUTTERFLY

RULE 4 — If still ambiguous, check arm pattern in the images:
- Both arms recover over the water simultaneously → BUTTERFLY
- Arms alternate (one pulls while other recovers) → FREESTYLE

=== CONFIDENCE CALIBRATION ===
Be HONEST about confidence. Do NOT default to "high".
- "high": Multiple rules clearly point to the same stroke AND the images clearly show the stroke pattern
- "medium": Rules point to one stroke but images are unclear, OR rules are ambiguous but images suggest a stroke
- "low": Rules conflict with each other, or data is missing/sparse, or you are not sure

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

Provide feedback in the following JSON format:
{{
  "detected_stroke": "<freestyle|backstroke|breaststroke|butterfly|unknown>",
  "stroke_confidence": "<high|medium|low>",
  "stroke_reasoning": "<brief explanation of how you identified the stroke>",
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
