import "./FeedbackDisplay.css";

const SEVERITY_COLORS = {
  high: "#e74c3c",
  medium: "#f39c12",
  low: "#27ae60",
};

function FeedbackDisplay({ feedback }) {
  if (!feedback) return null;

  return (
    <div className="feedback">
      {/* Detected Stroke */}
      {feedback.detected_stroke && (
        <div className="detected-stroke">
          Detected stroke: <strong>{feedback.detected_stroke}</strong>
          {feedback.stroke_confidence && <span> ({feedback.stroke_confidence} confidence)</span>}
        </div>
      )}

      {/* Pose Warning */}
      {feedback.pose_warning && (
        <div className="warning-banner">{feedback.pose_warning}</div>
      )}

      {/* Overall Score */}
      {feedback.overall_score && (
        <div className="score-card">
          <div className="score-number">{feedback.overall_score}/10</div>
          <p className="score-summary">{feedback.summary}</p>
        </div>
      )}

      {/* Strengths */}
      {feedback.strengths?.length > 0 && (
        <section className="feedback-section">
          <h2>Strengths</h2>
          <ul className="strengths-list">
            {feedback.strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </section>
      )}

      {/* Issues */}
      {feedback.issues?.length > 0 && (
        <section className="feedback-section">
          <h2>Areas to Improve</h2>
          {feedback.issues.map((issue, i) => (
            <div key={i} className="issue-card">
              <div className="issue-header">
                <h3>{issue.title}</h3>
                <span
                  className="severity-badge"
                  style={{ background: SEVERITY_COLORS[issue.severity] }}
                >
                  {issue.severity}
                </span>
              </div>
              <p>{issue.description}</p>
              <p className="suggestion"><strong>Fix:</strong> {issue.suggestion}</p>
              {issue.drill && (
                <p className="drill"><strong>Drill:</strong> {issue.drill}</p>
              )}
            </div>
          ))}
        </section>
      )}

      {/* Dryland Exercises */}
      {feedback.dryland_exercises?.length > 0 && (
        <section className="feedback-section">
          <h2>Dryland Exercises</h2>
          <div className="exercises-grid">
            {feedback.dryland_exercises.map((ex, i) => (
              <div key={i} className="exercise-card">
                <h3>{ex.name}</h3>
                <p>{ex.description}</p>
                <p className="exercise-purpose"><strong>Why:</strong> {ex.purpose}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default FeedbackDisplay;
