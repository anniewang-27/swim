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


def get_swim_feedback(
    angles: list[dict],
    pose_results: list[dict],
    stroke: str,
) -> dict:
    """
    Send angle data + annotated frame images to Gemini
    and get structured swim technique feedback.
    """
    api_key = os.getenv("GEMINI_API_KEY")

    # Build a summary of the angle data across frames
    angle_summary = json.dumps(angles, indent=2, default=str)

    prompt = f"""You are an expert swim coach analyzing a swimmer's {stroke} technique.

I'm providing you with:
1. Annotated frame images from the swim video (with pose skeleton overlay)
2. Joint angle data extracted from those frames

Joint angle data per frame (degrees):
{angle_summary}

Analyze BOTH the images and the angle data to provide technique feedback.
Look at body position, head alignment, arm entry, catch position, kick depth,
hip rotation, and overall streamline.

Provide feedback in the following JSON format:
{{
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

    # Build multimodal parts: images + text prompt
    parts = []

    # Add annotated frames as images
    for i, result in enumerate(pose_results):
        frame = result.get("annotated_frame")
        if frame is not None and len(result.get("keypoints", [])) > 0:
            b64 = _frame_to_base64(frame)
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

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    # Retry up to 3 times on rate limit
    for attempt in range(3):
        response = requests.post(url, json={
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192,
            }
        })

        if response.status_code == 429:
            wait = 2 ** attempt
            logger.warning(f"Gemini rate limited, retrying in {wait}s (attempt {attempt+1}/3)")
            time.sleep(wait)
            continue

        if not response.ok:
            raise Exception(f"Gemini API error ({response.status_code}): {response.text}")
        break
    else:
        raise Exception("Gemini API rate limit — please wait a moment and try again")

    data = response.json()

    # Gemini 2.5 may return multiple parts (thinking + response)
    # Grab the last text part which contains the actual answer
    resp_parts = data["candidates"][0]["content"]["parts"]
    response_text = ""
    for part in resp_parts:
        if "text" in part:
            response_text = part["text"]

    logger.info(f"Gemini returned {len(resp_parts)} parts")
    for i, p in enumerate(resp_parts):
        if "text" in p:
            logger.info(f"  Part {i} (text, {len(p['text'])} chars): {p['text'][:100]}...")
        elif "thought" in p:
            logger.info(f"  Part {i} (thought, {len(p.get('thought',''))} chars)")
    logger.info(f"Raw Gemini response (first 500 chars): {response_text[:500]}")

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
