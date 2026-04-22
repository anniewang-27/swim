"""
Export MediaPipe-annotated frames from a video as PNG images.

Usage:
    python export_annotated_frames.py <video_path> [output_dir]

Example:
    python export_annotated_frames.py ~/Downloads/butterfly.mp4 ./debug_frames
"""
import sys
import os
import cv2

from video_processing import extract_key_frames
from pose_estimation import estimate_poses


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    video_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "debug_frames"

    if not os.path.exists(video_path):
        print(f"Error: video not found at {video_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(f"Extracting frames from {video_path}...")
    frames = extract_key_frames(video_path)
    print(f"Extracted {len(frames)} frames")

    print("Running MediaPipe pose estimation...")
    results = estimate_poses(frames)

    # Save both original and annotated frames side by side
    for i, (frame, result) in enumerate(zip(frames, results)):
        kp_count = len(result["keypoints"])
        annotated = result["annotated_frame"]

        # Save original
        orig_path = os.path.join(output_dir, f"frame_{i:02d}_original.png")
        cv2.imwrite(orig_path, frame)

        # Save annotated
        ann_path = os.path.join(output_dir, f"frame_{i:02d}_annotated.png")
        cv2.imwrite(ann_path, annotated)

        # Side-by-side comparison
        h, w = frame.shape[:2]
        combined = cv2.hconcat([frame, annotated])
        combo_path = os.path.join(output_dir, f"frame_{i:02d}_comparison.png")
        cv2.imwrite(combo_path, combined)

        print(f"  Frame {i}: {kp_count} keypoints detected → saved")

    print(f"\nDone. {len(frames) * 3} files saved to {output_dir}/")


if __name__ == "__main__":
    main()
