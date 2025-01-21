import cv2
from cv2_enumerate_cameras import enumerate_cameras

def initialize_camera(camera_index):
    """
    Initialize a camera with the given index.
    
    Args:
        camera_index (int): Index of the camera to initialize
        
    Returns:
        tuple: (cv2.VideoCapture, bool) - The camera object and success status
    """
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    
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