import { useState } from "react";
import VideoUpload from "./components/VideoUpload";
import FeedbackDisplay from "./components/FeedbackDisplay";
import "./App.css";

function App() {
  const [feedback, setFeedback] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Swim Technique Analyzer</h1>
        <p>Upload a video of your swimming to get AI-powered feedback</p>
      </header>

      <main className="app-main">
        <VideoUpload
          onFeedback={setFeedback}
          onLoading={setLoading}
          onError={setError}
        />

        {loading && (
          <div className="loading">
            <div className="spinner" />
            <p>Analyzing your swim technique...</p>
          </div>
        )}

        {error && <div className="error-banner">{error}</div>}

        {feedback && <FeedbackDisplay feedback={feedback} />}
      </main>

      <footer className="app-footer">
        <p>
          <strong>Disclaimer:</strong> This tool uses AI and computer vision to analyze swim technique.
          AI can make mistakes — feedback may be inaccurate or incomplete. Always use your own judgment,
          and consult a qualified coach for personalized guidance. This tool is not a substitute for
          professional instruction.
        </p>
      </footer>
    </div>
  );
}

export default App;
