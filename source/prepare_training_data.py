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

# Example usage
video_path = './Data/Cut/left2.mp4'
output_directory = './Data/Compiled/candle/left'
batch_count = 5
alpha = 0.5

compile_video_frames(video_path, output_directory, batch_count, alpha)






def create_image_collage(folder_path, collage_size, output_path):
    """
    Creates a collage from images in a specified folder.

    Parameters:
    - folder_path: str, path to the folder containing images.
    - collage_size: tuple, number of images in the collage in the form (rows, columns).
    - output_path: str, path to save the resulting collage image.
    """
    # Supported image extensions
    supported_extensions = ('.jpg', '.jpeg', '.png', '.bmp')

    # List to hold the image paths
    image_paths = [
        os.path.join(folder_path, filename)
        for filename in os.listdir(folder_path)
        if filename.lower().endswith(supported_extensions)
    ]

    # Ensure we have enough images for the collage
    if len(image_paths) < collage_size[0] * collage_size[1]:
        print("Not enough images to create the collage.")
        return

    # Read the first few images to determine the size of the collage
    images = [cv2.imread(image_path) for image_path in image_paths[:collage_size[0] * collage_size[1]]]

    # Resize images to the smallest dimensions among them for uniformity
    min_height = min(image.shape[0] for image in images)
    min_width = min(image.shape[1] for image in images)
    resized_images = [cv2.resize(image, (min_width, min_height)) for image in images]

    # Create the collage
    collage_height = min_height * collage_size[0]
    collage_width = min_width * collage_size[1]
    collage = np.zeros((collage_height, collage_width, 3), dtype=np.uint8)

    # Fill the collage with images
    for idx, image in enumerate(resized_images):
        row = idx // collage_size[1]
        col = idx % collage_size[1]
        collage[row * min_height: (row + 1) * min_height, col * min_width: (col + 1) * min_width] = image
    
    # Ensure the output directory exists
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    # Save the collage to the specified output path
    cv2.imwrite(output_path, collage)
    print(f"Collage saved to {output_path}")

# Example usage
collage_size = (3, 10)  # 3 rows and 3 columns
output_path = os.path.join(output_directory, 'Collage/collage.jpg')

# create_image_collage(output_directory, collage_size, output_path)