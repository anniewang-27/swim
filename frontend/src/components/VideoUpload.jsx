import { useState, useRef } from "react";
import axios from "axios";
import "./VideoUpload.css";

const API_URL = "http://localhost:8000";

const STROKES = [
  { value: "freestyle", label: "Freestyle" },
  { value: "butterfly", label: "Butterfly" },
  { value: "backstroke", label: "Backstroke" },
  { value: "breaststroke", label: "Breaststroke" },
];

function VideoUpload({ onFeedback, onLoading, onError }) {
  const [file, setFile] = useState(null);
  const [stroke, setStroke] = useState("freestyle");
  const [preview, setPreview] = useState(null);
  const inputRef = useRef();

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (!selected) return;
    setFile(selected);
    setPreview(URL.createObjectURL(selected));
    onError(null);
    onFeedback(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    onLoading(true);
    onError(null);
    onFeedback(null);

    const formData = new FormData();
    formData.append("video", file);
    formData.append("stroke", stroke);

    try {
      const res = await axios.post(`${API_URL}/analyze`, formData);
      console.log("API response:", JSON.stringify(res.data, null, 2));

      onFeedback({
        ...res.data.feedback,
        _meta: {
          stroke_hint: res.data.stroke_hint,
          detected_stroke: res.data.detected_stroke,
          detected_confidence: res.data.detected_confidence,
          frames_analyzed: res.data.frames_analyzed,
        },
        _angles: res.data.angles,
        _angleDebug: res.data.angle_debug,
        _stroke_metrics: res.data.stroke_metrics,
        _keypoints: res.data.keypoints,
      });
    } catch (err) {
      onError(err.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      onLoading(false);
    }
  };

  return (
    <form className="upload-card" onSubmit={handleSubmit}>
      <div
        className="drop-zone"
        onClick={() => inputRef.current.click()}
      >
        {preview ? (
          <video src={preview} controls className="preview-video" />
        ) : (
          <p>Click to select a swim video</p>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          hidden
          onChange={handleFileChange}
        />
      </div>

      <div className="upload-controls">
        <select value={stroke} onChange={(e) => setStroke(e.target.value)}>
          {STROKES.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>

        <button type="submit" disabled={!file}>
          Analyze Technique
        </button>
      </div>
    </form>
  );
}

export default VideoUpload;
