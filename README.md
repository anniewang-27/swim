# Swim Technique Analyzer

A web application that analyzes swimming technique from uploaded videos using computer vision and AI. Upload a video of your swimming, and get personalized feedback on your form, suggested drills, and dryland exercises.

## Architecture

```
User uploads video (React)
  → FastAPI backend
  → OpenCV extracts key frames
  → MediaPipe Pose detects 33 body keypoints per frame
  → Joint angles calculated (elbow, shoulder, hip, knee)
  → Keypoint + angle data sent to Claude API
  → Claude returns structured JSON feedback
  → Frontend renders feedback, drills, and exercises
```

## Tech Stack

- **Frontend:** React + Vite
- **Backend:** FastAPI (Python)
- **Computer Vision:** OpenCV + MediaPipe Pose
- **AI Feedback:** Claude API (Anthropic)

## Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and the backend at `http://localhost:8000`.

## Usage

1. Open the app in your browser
2. Click to upload a swim video
3. Select your stroke type (freestyle, butterfly, backstroke, breaststroke)
4. Click "Analyze Technique"
5. Review your feedback: overall score, strengths, areas to improve, drills, and dryland exercises
