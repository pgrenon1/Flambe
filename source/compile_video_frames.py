import cv2
import os
import numpy as np

def compile_video_frames(video_path, output_directory, batch_count, alpha):
    """
    Splits a video into frames, compiles them in batches with alpha blending, and saves the compiled images.

    Parameters:
    - video_path: str, path to the input video file.
    - output_directory: str, directory where the compiled images will be saved.
    - batch_count: int, number of frames to process in each batch.
    - alpha: float, blending factor for overlaying images (0 < alpha < 1).
    """
    # Ensure output directory exists
    os.makedirs(output_directory, exist_ok=True)

    # Get the base name of the video (without extension)
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    # Capture the video
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    frame_count = 0
    compiled_frame_count = 0
    compiled_image = None

    while True:
        # Read a frame from the video
        ret, frame = cap.read()
        if not ret:
            break  # Exit if there are no more frames

        # Initialize compiled_image on first frame of the batch
        if frame_count % batch_count == 0:
            compiled_image = np.zeros_like(frame)

        # Overlay the current frame with the compiled image using cv2.addWeighted
        compiled_image = cv2.addWeighted(compiled_image, 1 - alpha, frame, alpha, 0)

        # If we have processed enough frames for the current batch
        if (frame_count + 1) % batch_count == 0 or ret == False:
            # Define the output filename based on the video name and the range of frames
            start_frame = frame_count - (batch_count - 1)
            end_frame = frame_count
            output_filename = os.path.join(output_directory, f"{video_name}_{start_frame:03d}-{end_frame:03d}.jpg")

            # Save the compiled image for the batch
            cv2.imwrite(output_filename, compiled_image)
            print(f"Compiled image saved to {output_filename}")

            compiled_frame_count += 1

        frame_count += 1

    # Release the video capture object
    cap.release()
    print(f"Processed {frame_count} frames, created {compiled_frame_count} compiled images.")

video_path = './data/raw/neutral015.mp4'
output_directory = './data/compiled/candle/neutral'
batch_count = 5
alpha = 0.5

compile_video_frames(video_path, output_directory, batch_count, alpha)

