import os
import time
import logging
import tempfile
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from video_processing import extract_key_frames
from pose_estimation import estimate_poses
from angle_calculation import calculate_all_angles
from claude_feedback import get_swim_feedback, detect_stroke

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("swim")

app = FastAPI(title="Swim Technique Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze_video(
    video: UploadFile = File(...),
    stroke: str = Form("freestyle"),
):
    """
    Accept a swim video, extract frames, run pose estimation,
    calculate angles, and return AI-generated feedback.
    """
    # Save uploaded video to a temp file
    suffix = os.path.splitext(video.filename or ".mp4")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await video.read())
        tmp_path = tmp.name

    try:
        t0 = time.time()
        logger.info(f"[1/5] Extracting frames from video ({video.filename})...")
        frames = extract_key_frames(tmp_path)
        logger.info(f"[1/5] Done — extracted {len(frames)} frames in {time.time()-t0:.1f}s")

        t1 = time.time()
        logger.info(f"[2/5] Running MediaPipe pose estimation on {len(frames)} frames...")
        pose_results = estimate_poses(frames)
        keypoint_counts = [len(r["keypoints"]) for r in pose_results]
        logger.info(f"[2/5] Done — keypoints per frame: {keypoint_counts} in {time.time()-t1:.1f}s")

        t_stroke = time.time()
        logger.info("[2.5/5] Detecting stroke type...")
        stroke_result = detect_stroke(frames, pose_results)
        detected = stroke_result.get("detected_stroke", "unknown")
        confidence = stroke_result.get("confidence", "low")
        logger.info(f"[2.5/5] Detected stroke: {detected} (confidence: {confidence}) in {time.time()-t_stroke:.1f}s")

        if detected != "unknown" and detected != stroke.lower() and confidence in ("high", "medium"):
            return JSONResponse(content={
                "stroke_mismatch": True,
                "selected_stroke": stroke,
                "detected_stroke": detected,
                "confidence": confidence,
                "message": f"It looks like this video shows {detected}, but you selected {stroke}. Please select the correct stroke and try again.",
            })

        t2 = time.time()
        logger.info("[3/5] Calculating joint angles...")
        angles = calculate_all_angles(pose_results)
        logger.info(f"[3/4] Done — angles for {len(angles)} frames in {time.time()-t2:.1f}s")
        for i, a in enumerate(angles):
            logger.info(f"  Frame {i}: {a}")

        t3 = time.time()
        logger.info("[5/5] Sending data to Gemini API for feedback...")
        feedback = get_swim_feedback(
            angles=angles,
            pose_results=pose_results,
            stroke=stroke,
        )
        logger.info(f"[5/5] Done — got feedback in {time.time()-t3:.1f}s")
        logger.info(f"Total pipeline time: {time.time()-t0:.1f}s")

        return JSONResponse(content={
            "stroke": stroke,
            "frames_analyzed": len(frames),
            "feedback": feedback,
        })
    except Exception as e:
        logger.error(f"Pipeline failed: {type(e).__name__}: {e}")
        error_msg = str(e)
        if "credit balance" in error_msg.lower():
            return JSONResponse(status_code=402, content={
                "detail": "Anthropic API credits are too low. Please add credits at console.anthropic.com/settings/billing"
            })
        # Sanitize error message to avoid leaking API keys
        safe_msg = error_msg.split("?key=")[0] if "?key=" in error_msg else error_msg
        return JSONResponse(status_code=500, content={"detail": safe_msg})
    finally:
        os.unlink(tmp_path)
