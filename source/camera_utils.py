import cv2
import os
import platform

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

def connect_ip_camera(ip_address, port="8080"):
    """
    Connect to a mobile phone camera using IP Webcam app.
    
    Args:
        ip_address (str): IP address of the phone (e.g., "192.168.1.100")
        port (str): Port number (default "8080")
        
    Returns:
        tuple: (cv2.VideoCapture, bool) - The camera object and success status
    """
    # Construct the URL for the IP Webcam stream
    url = f"http://{ip_address}:{port}/video"
    
    try:
        # Try to connect to the IP camera
        cap = cv2.VideoCapture(url)
        
        # Test if connection is successful
        if not cap.isOpened():
            print(f"Error: Could not connect to IP camera at {url}")
            return cap, False
            
        # Try to read a test frame
        ret, frame = cap.read()
        if not ret:
            print(f"Error: Could not read frame from IP camera at {url}")
            cap.release()
            return cap, False
            
        print(f"Successfully connected to IP camera at {url}")
        return cap, True
        
    except Exception as e:
        print(f"Error connecting to IP camera: {str(e)}")
        return None, False

def detect_cameras():
    """
    Detect all available cameras connected to the system.
    
    Returns:
        list: List of tuples containing (index, name) of available cameras
    """
    available_cameras = []
    
    # Test camera indices from 0 to 9
    for index in range(10):
        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            continue
            
        if cap.read()[0]:
            camera_name = f"Camera {index}"
            available_cameras.append((index, camera_name))
            
        cap.release()
    
    # If no cameras found, add default camera
    if not available_cameras:
        available_cameras.append((0, "Default Camera"))
        
    return sorted(available_cameras) 