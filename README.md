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
