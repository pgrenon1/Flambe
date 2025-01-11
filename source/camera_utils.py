import cv2

def initialize_camera(camera_index):
    """
    Initialize a camera with the given index.
    
    Args:
        camera_index (int): Index of the camera to initialize
        
    Returns:
        tuple: (cv2.VideoCapture, bool) - The camera object and success status
    """
    cap = cv2.VideoCapture(camera_index)
    
    # Check if the webcam is opened successfully
    if not cap.isOpened():
        print(f"Error: Could not open webcam at index {camera_index}. Please check the device connection and index.")
        return cap, False
        
    return cap, True 