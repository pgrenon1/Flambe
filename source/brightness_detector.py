import cv2
import numpy as np
from camera_utils import initialize_camera
import argparse

def find_brightest_point(frame):
    """
    Find the brightest point in the frame and its position relative to center.
    Returns (x_offset, y_offset) where negative values mean left/up and positive values mean right/down.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (11, 11), 0)
    
    # Find the brightest point
    (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(blurred)
    
    # Get frame dimensions
    height, width = frame.shape[:2]
    center_x, center_y = width // 2, height // 2
    
    # Calculate offset from center (-1.0 to 1.0)
    x_offset = (maxLoc[0] - center_x) / (width / 2)
    y_offset = (maxLoc[1] - center_y) / (height / 2)
    
    return maxLoc, (x_offset, y_offset), maxVal

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--camera-index', type=int, default=0,
                       help='Index of the camera to use')
    args = parser.parse_args()
    
    # Initialize camera
    cap, success = initialize_camera(args.camera_index)
    if not success:
        return
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break
                
            # Find brightest point and its relative position
            bright_point, offsets, brightness = find_brightest_point(frame)
            
            # Draw crosshair at brightest point
            x, y = bright_point
            cv2.drawMarker(frame, (x, y), (0, 255, 0), cv2.MARKER_CROSS, 20, 2)
            
            # Draw center crosshair
            height, width = frame.shape[:2]
            center = (width // 2, height // 2)
            cv2.drawMarker(frame, center, (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
            
            # Add text showing relative position and brightness
            text = f"X: {offsets[0]:.2f}, Y: {offsets[1]:.2f}, Brightness: {brightness:.0f}"
            cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                       1, (0, 255, 0), 2)
            
            # Show the frame
            cv2.imshow('Brightness Detector', frame)
            
            # Break loop on 'q' press or window close
            if cv2.waitKey(1) & 0xFF == ord('q') or \
               cv2.getWindowProperty('Brightness Detector', cv2.WND_PROP_VISIBLE) < 1:
                break
                
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main() 