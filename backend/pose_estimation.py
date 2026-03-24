import cv2
import numpy as np
import mediapipe as mp

mp_pose = mp.solutions.pose


def estimate_poses(frames: list[np.ndarray]) -> list[dict]:
    """
    Run MediaPipe Pose on each frame.
    Returns a list of dicts, one per frame:
      {
        "keypoints": [ {id, name, x, y, z, visibility}, ... ],   # 33 landmarks
        "annotated_frame": np.ndarray   # frame with skeleton drawn
      }
    """
    results: list[dict] = []

    with mp_pose.Pose(
        static_image_mode=True,
        model_complexity=2,
        min_detection_confidence=0.5,
    ) as pose:
        for frame in frames:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            detection = pose.process(rgb)

            keypoints = []
            annotated = frame.copy()

            if detection.pose_landmarks:
                for idx, lm in enumerate(detection.pose_landmarks.landmark):
                    keypoints.append({
                        "id": idx,
                        "name": mp_pose.PoseLandmark(idx).name,
                        "x": lm.x,
                        "y": lm.y,
                        "z": lm.z,
                        "visibility": lm.visibility,
                    })

                # Draw skeleton on annotated frame
                mp.solutions.drawing_utils.draw_landmarks(
                    annotated,
                    detection.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                )

            results.append({
                "keypoints": keypoints,
                "annotated_frame": annotated,
            })

    return results
