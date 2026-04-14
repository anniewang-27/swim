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

        {feedback && (
          <>
            <FeedbackDisplay feedback={feedback} />
            <details style={{marginTop: "1rem"}}>
              <summary>Debug: Stroke Metrics</summary>
              <pre style={{fontSize: "0.8rem", overflow: "auto"}}>{JSON.stringify(feedback._stroke_metrics, null, 2)}</pre>
            </details>
            <details style={{marginTop: "0.5rem"}}>
              <summary>Debug: Angles per Frame</summary>
              <pre style={{fontSize: "0.8rem", overflow: "auto"}}>{JSON.stringify(feedback._angles, null, 2)}</pre>
            </details>
            <details style={{marginTop: "0.5rem"}}>
              <summary>Debug: Why Angles Were Missing</summary>
              <pre style={{fontSize: "0.8rem", overflow: "auto"}}>{JSON.stringify(feedback._angleDebug, null, 2)}</pre>
            </details>
            <details style={{marginTop: "0.5rem"}}>
              <summary>Debug: MediaPipe Keypoints per Frame</summary>
              <pre style={{fontSize: "0.8rem", overflow: "auto"}}>{JSON.stringify(feedback._keypoints, null, 2)}</pre>
            </details>
            <details style={{marginTop: "0.5rem"}}>
              <summary>Debug: Raw API response</summary>
              <pre style={{fontSize: "0.8rem", overflow: "auto"}}>{JSON.stringify(feedback, null, 2)}</pre>
            </details>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
