import cv2
import os
from pynput import keyboard
import numpy as np

# Define directories for each arrow key
directories = {
    "up": "frames/up",
    "down": "frames/down",
    "left": "frames/left",
    "right": "frames/right"
}

# Create directories if they don't exist
for direction, path in directories.items():
    os.makedirs(path, exist_ok=True)

# Initialize the webcam
cap = cv2.VideoCapture(4)

# Check if the webcam is opened successfully
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("Press arrow keys to save blended batches. Press 'q' to quit.")

frame_count = 0
batch_size = 5  # Number of frames to blend in a batch
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
        elif key.char == 'q':  # Quit on 'q'
            print("Quitting...")
            return False
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
    # Release the webcam and close all OpenCV windows
    cap.release()
    cv2.destroyAllWindows()
    listener.stop()
