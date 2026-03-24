import cv2
import numpy as np

# Target number of evenly-spaced frames to sample from the video.
TARGET_FRAMES = 10


def extract_key_frames(video_path: str, target_frames: int = TARGET_FRAMES) -> list[np.ndarray]:
    """
    Open a video file and extract *target_frames* evenly-spaced frames.
    Returns a list of BGR numpy arrays.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        raise ValueError("Video has no frames")

    # Pick evenly spaced frame indices
    indices = np.linspace(0, total_frames - 1, min(target_frames, total_frames), dtype=int)

    frames: list[np.ndarray] = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if ret:
            frames.append(frame)

    cap.release()
    return frames
