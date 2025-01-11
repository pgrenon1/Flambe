import cv2
import os
from pynput import keyboard
import numpy as np
import argparse
from camera_utils import initialize_camera

# Add at the start of the file, before other initialization
parser = argparse.ArgumentParser()
parser.add_argument('--camera-index', type=int, default=0,
                   help='Index of the camera to use')
args = parser.parse_args()

# Define directories for each arrow key
directories = {
    "up": "frames/forward",
    "down": "frames/back",
    "left": "frames/left",
    "right": "frames/right"
}

# Create directories if they don't exist
for direction, path in directories.items():
    os.makedirs(path, exist_ok=True)

# Initialize the webcam using the utility function
cap, success = initialize_camera(args.camera_index)
if not success:
    exit()

print("Press arrow keys to save blended batches. Press 'Enter' or 'Space' to proceed.")

frame_count = 0
batch_size = 5  # Number of frames to blend in a batch
if batch_size <= 0:
    raise ValueError("batch_size must be greater than 0.")

current_batch = None
frames_in_batch = 0
active_key = None  # Track the currently pressed key
alpha = 1 / batch_size  # Fixed alpha value for blending

def on_press(key):
    global active_key
    try:
        if key == keyboard.Key.up:
            active_key = "up"
        elif key == keyboard.Key.down:
            active_key = "down"
        elif key == keyboard.Key.left:
            active_key = "left"
        elif key == keyboard.Key.right:
            active_key = "right"
        elif key == keyboard.Key.enter or key == keyboard.Key.space:
            print("Program terminated by user.")
            os._exit(0)  # Force quit the program
    except AttributeError:
        pass

def on_release(key):
    global active_key
    active_key = None

# Start listening to keyboard events
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

try:
    while True:
        # Capture a frame from the webcam
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break

        # Display the frame
        cv2.imshow("Webcam", frame)

        # Check if the user closed the window
        if cv2.getWindowProperty("Webcam", cv2.WND_PROP_VISIBLE) < 1:
            print("Webcam window closed. Terminating program.")
            break

        # Add the frame to the current batch if an arrow key is active
        if active_key in directories:
            if frames_in_batch == 0:
                # Initialize the batch with the first frame (converted to float for blending)
                current_batch = frame.astype(np.float32) * alpha
            else:
                # Add the new frame to the batch using a constant alpha
                current_batch = cv2.addWeighted(current_batch, 1, frame.astype(np.float32), alpha, 0)

            frames_in_batch += 1

            # Save the batch as an image when it's full
            if frames_in_batch == batch_size:
                frame_count += 1
                filepath = os.path.join(directories[active_key], f"batch_{frame_count}.jpg")
                cv2.imwrite(filepath, current_batch.astype(np.uint8))
                print(f"Saved batch to {filepath}")
                current_batch = None
                frames_in_batch = 0

        # Add a small delay to prevent high CPU usage
        if cv2.waitKey(1) & 0xFF == ord('q'):  # Quit on 'q'
            break

except KeyboardInterrupt:
    print("\nProgram interrupted.")

finally:
    try:
        listener.stop()
    except Exception as e:
        print(f"Error stopping listener: {e}")
    cap.release()
    cv2.destroyAllWindows()