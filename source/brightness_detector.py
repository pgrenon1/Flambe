import cv2
import numpy as np
from camera_utils import initialize_camera, connect_ip_camera
import argparse

def mouse_callback(event, x, y, flags, param):
    """Handle mouse events to set rectangle origin and adjust threshold"""
    if event == cv2.EVENT_LBUTTONDOWN:
        param['drawing'] = True
        param['origin'] = [(x, y), (x, y)]
    elif event == cv2.EVENT_MOUSEMOVE:
        if param.get('drawing', False):
            param['origin'][1] = (x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        param['drawing'] = False
        param['origin'][1] = (x, y)
    elif event == cv2.EVENT_MOUSEWHEEL:
        # Windows mouse wheel
        delta = flags > 0 and 1 or -1
        param['threshold'] = min(1.0, max(0.0, param['threshold'] + delta * 0.05))
    elif event == cv2.EVENT_MOUSEHWHEEL:
        # Linux/Mac mouse wheel
        delta = flags < 0 and 1 or -1
        param['threshold'] = min(1.0, max(0.0, param['threshold'] + delta * 0.05))

def point_in_rectangle(point, rect):
    """Check if a point is inside a rectangle"""
    x, y = point
    (x1, y1), (x2, y2) = rect
    left, right = min(x1, x2), max(x1, x2)
    top, bottom = min(y1, y2), max(y1, y2)
    return left <= x <= right and top <= y <= bottom

def get_rectangle_center(rect):
    """Get the center point of a rectangle"""
    (x1, y1), (x2, y2) = rect
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2
    return (center_x, center_y)

class ImageFilter:
    def __init__(self):
        self.filters = {
            "None": lambda frame: cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
            "Gaussian Blur": lambda frame: cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (11, 11), 0),
            "Contrast Enhanced": lambda frame: cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)),
            "Threshold": lambda frame: cv2.threshold(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 127, 255, cv2.THRESH_BINARY)[1],
            "Edge Detection": lambda frame: cv2.Canny(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 100, 200)
        }
        self.filter_names = list(self.filters.keys())
        self.current_filter_idx = 0
    
    def apply(self, frame):
        current_filter = self.filter_names[self.current_filter_idx]
        return self.filters[current_filter](frame)
    
    def next_filter(self):
        self.current_filter_idx = (self.current_filter_idx + 1) % len(self.filter_names)
        return self.filter_names[self.current_filter_idx]
    
    def prev_filter(self):
        self.current_filter_idx = (self.current_filter_idx - 1) % len(self.filter_names)
        return self.filter_names[self.current_filter_idx]
    
    def get_current_filter(self):
        return self.filter_names[self.current_filter_idx]
    
    def set_filter(self, filter_name):
        if filter_name in self.filters:
            self.current_filter_idx = self.filter_names.index(filter_name)

def find_bright_region(frame, rect, image_filter, threshold_percentage=0.8):
    """
    Find the region of high brightness in the frame and its position relative to rectangle.
    
    Args:
        frame: Input frame
        rect: Rectangle coordinates [(x1,y1), (x2,y2)]
        image_filter: ImageFilter instance
        threshold_percentage: Percentage of max brightness to consider as "bright"
    
    Returns:
        tuple: (center_point, direction_vector, bright_mask)
    """
    # Apply selected filter
    processed = image_filter.apply(frame)
    
    # Find the maximum brightness value
    max_val = np.max(processed)
    
    # Create a mask of bright pixels
    brightness_threshold = int(max_val * threshold_percentage)
    _, bright_mask = cv2.threshold(processed, brightness_threshold, 255, cv2.THRESH_BINARY)
    
    # Find contours of bright regions
    contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    rect_center = get_rectangle_center(rect)
    
    if not contours:
        return rect_center, (0, 0), bright_mask
    
    # Find the largest bright region
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Get the center of the bright region
    M = cv2.moments(largest_contour)
    if M["m00"] == 0:
        center_point = rect_center
    else:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        center_point = (cx, cy)
    
    # If bright point is inside rectangle, return zero vector
    if point_in_rectangle(center_point, rect):
        return center_point, (0, 0), bright_mask
    
    # Calculate vector from rectangle center to bright region center
    dx = center_point[0] - rect_center[0]
    dy = center_point[1] - rect_center[1]
    
    # Calculate vector magnitude
    magnitude = np.sqrt(dx*dx + dy*dy)
    
    # Normalize vector (if magnitude is not zero)
    if magnitude > 0:
        direction_vector = (dx/magnitude, dy/magnitude)
    else:
        direction_vector = (0, 0)
    
    return center_point, direction_vector, bright_mask

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--camera-index', type=str, default="0",
                       help='Index of the camera to use or ip:address:port for IP camera')
    parser.add_argument('--filter', type=str, default="None",
                       help='Initial filter to apply')
    args = parser.parse_args()
    
    # Initialize camera
    if args.camera_index.startswith("ip:"):
        _, ip, port = args.camera_index.split(":")
        cap, success = connect_ip_camera(ip, port)
    else:
        cap, success = initialize_camera(int(args.camera_index))
    
    if not success:
        return
    
    # Create window and set mouse callback
    window_name = 'Brightness Detector'
    cv2.namedWindow(window_name)
    
    # Initialize filter system
    image_filter = ImageFilter()
    image_filter.set_filter(args.filter)
    
    # Store rectangle points, drawing state, and threshold in a dict
    state = {
        'origin': [(0, 0), (0, 0)],
        'drawing': False,
        'show_filtered': False,
        'threshold': 0.8  # Initial threshold value
    }
    cv2.setMouseCallback(window_name, mouse_callback, state)
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break
            
            # Apply filter and find bright region using current threshold
            filtered_frame = image_filter.apply(frame)
            center_point, direction, mask = find_bright_region(
                frame, state['origin'], image_filter, state['threshold'])
            
            # Choose which frame to display based on filter state
            display_frame = frame
            if state['show_filtered']:
                display_frame = cv2.cvtColor(filtered_frame, cv2.COLOR_GRAY2BGR)
                
                # Add text showing information (only in filtered view)
                texts = [
                    f"Vector: ({direction[0]:.2f}, {direction[1]:.2f})",
                    f"Filter: {image_filter.get_current_filter()}",
                    f"Threshold: {state['threshold']:.2f}"
                ]
                
                for i, text in enumerate(texts):
                    cv2.putText(display_frame, text, (10, 30 + i*30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Draw rectangle
            cv2.rectangle(display_frame, state['origin'][0], state['origin'][1], (0, 0, 255), 2)
            
            # Draw rectangle center
            rect_center = get_rectangle_center(state['origin'])
            cv2.drawMarker(display_frame, rect_center, (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
            
            # Draw bright region center
            cv2.drawMarker(display_frame, center_point, (0, 255, 0), cv2.MARKER_CROSS, 20, 2)
            
            # Draw direction vector
            vector_scale = 100
            vector_end = (
                int(rect_center[0] + direction[0] * vector_scale),
                int(rect_center[1] + direction[1] * vector_scale)
            )
            cv2.arrowedLine(display_frame, rect_center, vector_end, (255, 0, 0), 2)
            
            # Show the frame
            cv2.imshow(window_name, display_frame)
            
            # Handle key presses
            key = cv2.waitKeyEx(1)
            if key == ord('q') or \
               cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break
            elif key == ord('f'):
                state['show_filtered'] = not state['show_filtered']
            elif key in [81, 2424832]:  # Left arrow
                image_filter.prev_filter()
            elif key in [83, 2555904]:  # Right arrow
                image_filter.next_filter()
                
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main() 