import cv2
import os

def split_video_to_frames(video_path, output_folder):
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Extract the video name without extension
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    # Open the video file
    video = cv2.VideoCapture(video_path)

    if not video.isOpened():
        print("Error: Could not open video.")
        return

    frame_count = 0
    while True:
        # Read a frame from the video
        ret, frame = video.read()
        if not ret:
            break  # Exit the loop if there are no more frames

        # Save the frame with the video name prefix
        frame_filename = os.path.join(output_folder, f"{video_name}_{frame_count:04d}.jpg")
        cv2.imwrite(frame_filename, frame)
        frame_count += 1

    # Release the video capture object
    video.release()
    print(f"Extracted {frame_count} frames to {output_folder}")

# Usage example
split_video_to_frames("data/raw/forward1.mp4", "data/split/forward")
