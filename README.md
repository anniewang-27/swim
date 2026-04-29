# Swim Technique Analyzer

A web application that analyzes swimming technique from uploaded videos using computer vision and AI. Upload a video of your swimming, and get personalized feedback on your form, suggested drills, and dryland exercises.

## Architecture

```
User uploads video (React frontend)
  → FastAPI backend receives video
  → OpenCV extracts ~10 evenly-spaced key frames
  → MediaPipe Pose detects 33 body keypoints per frame
  → Joint angles calculated (elbow, shoulder, hip, knee)
  → Annotated frames (with skeleton overlay) + angle data sent to Gemini API
  → Gemini returns structured JSON feedback
  → Frontend renders score, issues, strengths, drills, and exercises
```

## Tech Stack

- **Frontend:** React + Vite
- **Backend:** FastAPI (Python 3.9+)
- **Computer Vision:** OpenCV + MediaPipe Pose
- **AI Feedback:** Gemini API (Google)

## Prerequisites

- Python 3.9+
- Node.js 18+
- A Gemini API key (free at https://aistudio.google.com/apikey)

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/anniewang-27/swim.git
cd swim
```

### 2. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create your `.env` file with your Gemini API key:

```bash
cp .env.example .env
```

Then edit `backend/.env` and replace `your-gemini-api-key-here` with your actual key.

Start the backend:

```bash
uvicorn main:app --reload
```

The backend runs at `http://localhost:8000`.

### 3. Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`.

### 4. Open the app

Go to http://localhost:5173 in your browser.

## Usage

1. Click the upload area to select a swim video (MP4, MOV, etc.)
2. Select your stroke type (freestyle, butterfly, backstroke, breaststroke)
3. Click **Analyze Technique**
4. Wait ~10-15 seconds for the analysis pipeline to run
5. Review your feedback: overall score, strengths, areas to improve, drills, and dryland exercises

## Project Structure

```
swim/
├── backend/
│   ├── main.py                # FastAPI app with /analyze endpoint
│   ├── video_processing.py    # OpenCV frame extraction
│   ├── pose_estimation.py     # MediaPipe pose detection + skeleton overlay
│   ├── angle_calculation.py   # Joint angle math from keypoints
│   ├── claude_feedback.py     # Gemini API integration (images + angles)
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                   # your API key (gitignored)
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main app with state management
│   │   └── components/
│   │       ├── VideoUpload.jsx     # Video upload + stroke selector
│   │       └── FeedbackDisplay.jsx # Renders AI feedback
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Troubleshooting

- **"Something went wrong"** — Check the backend terminal for detailed error logs
- **Rate limit errors (429)** — The Gemini free tier has daily limits. Wait a minute and try again, or use a different model
- **No keypoints detected** — Make sure the video shows the swimmer's body clearly, ideally filmed from the side
- **Backend won't start** — Make sure you activated the venv: `source venv/bin/activate`

## Open-Source Code & Attribution

This project is built on top of three external libraries / APIs, plus a substantial amount of custom code we wrote ourselves.

### What we used (open source / external)

| Library / API | Purpose | What it does for us |
|---|---|---|
| [**MediaPipe Pose**](https://developers.google.com/mediapipe/solutions/vision/pose_landmarker) (Apache 2.0) | Computer vision | 33-point body landmark detection per frame. We use the pre-trained model as-is — we did not retrain it. |
| [**OpenCV**](https://opencv.org/) (Apache 2.0) | Video I/O | Reading frames from uploaded video files. |
| [**Google Gemini API**](https://ai.google.dev/) | Multimodal LLM | Receives our images + computed metrics and returns structured JSON feedback. We use the public `generateContent` HTTP endpoint directly (no SDK). |
| **FastAPI**, **React**, **Vite** | App framework | Standard web framework boilerplate — used out of the box. |

We did **not** start from any open-source swim-analysis codebase or template. The pipeline, classification logic, prompt engineering, and UI are all original.

### Modifications and additions on top of the open-source pieces

1. **Custom pipeline orchestration (`backend/main.py`).** We wrote the `/analyze` endpoint that chains video extraction → pose estimation → angle math → metric aggregation → multimodal LLM call → response shaping. Includes graceful error handling, API key sanitization, and structured logging.

2. **Frame extraction strategy (`backend/video_processing.py`).** OpenCV gives us frame-by-frame access; we layered evenly-spaced sampling (target ~20 frames) on top so the LLM sees representative frames across the stroke cycle without being overwhelmed.

3. **Pose result post-processing (`backend/pose_estimation.py`).** We wrap MediaPipe's output, draw the skeleton overlay onto the frame, and return both the raw keypoints and the annotated image. None of this is in MediaPipe out of the box.

4. **Joint angle math (`backend/angle_calculation.py`).** Original implementation of 3-point cosine angle calculation across 8 swim-relevant joints (elbows, shoulders, hips, knees), with visibility filtering.

5. **Biomechanical metrics for stroke classification (`backend/angle_calculation.py`).** This is the largest piece of original work. Computes:
   - **Knee bend classification** using percentile-based reference (p10 for larger samples, median for small) so a single bad MediaPipe frame can't dominate
   - **Body undulation score** from the vertical motion of head, chest, and hips across frames (with frame-to-frame outlier filtering to suppress jitter)
   - **Wave-downward ratio** that detects whether the chest leads the hips in a butterfly-style undulation
   - **Kick pattern** (synchronized vs alternating) from left/right knee angle symmetry
   - **Data-quality gates** that mark metrics as `insufficient_data` when MediaPipe didn't give us reliable input

6. **Prompt engineering (`backend/claude_feedback.py`).** Sequential classification rules ordered by reliability of the underlying metric, with explicit conflict-resolution instructions and confidence calibration. Gemini was originally inconsistent (calling the same butterfly video freestyle on one run and breaststroke on another); the rules and metric grounding made it deterministic.

7. **Robust Gemini integration (`backend/claude_feedback.py`).** Multi-model fallback (`gemini-2.5-flash` → `2.0-flash` → `1.5-flash`) for when one model blocks underwater swim footage; lowered safety thresholds; retry logic for 429/503; markdown-fence stripping on JSON responses; helpful error messages distinguishing safety blocks, truncation, and quota issues.

8. **Frontend application (`frontend/src/`).** All React components (upload, feedback display, score card, severity badges, dryland exercise grid) are original. State management, axios integration, error banners, and CSS styling were written from scratch.

9. **Diagnostic tooling (`backend/export_annotated_frames.py`).** Standalone script that runs a video through the pose pipeline and writes annotated PNGs to disk — useful for understanding where MediaPipe failed and for grabbing presentation imagery.

### Lines-of-code rough breakdown

- **External libraries:** Imported via `pip` / `npm`, no source modifications.
- **Original code in this repo:** Effectively all of `backend/` (~700 lines) and `frontend/src/` (~400 lines) is our own.

### AI coding assistance

We used [**Claude Code**](https://claude.com/claude-code) (Anthropic's CLI coding agent) as a pair-programming tool throughout development. It helped us scaffold the initial FastAPI/React structure, debug MediaPipe noise issues, iterate on the Gemini prompt, generate the diagnostic script, and refactor the stroke classification logic. All architectural decisions, design choices, and code reviews were ours — Claude Code accelerated the work but did not replace our judgment.
