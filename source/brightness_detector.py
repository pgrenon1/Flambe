import cv2
import numpy as np
from camera_utils import initialize_camera, connect_ip_camera
import argparse

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

class BrightnessDetector:
    def __init__(self, camera_index="0", initial_filter="None"):
        self.camera_index = camera_index
        self.window_name = 'Flambé'
        self.state = {
            'origin': [(0, 0), (0, 0)],
            'drawing': False,
            'show_filtered': False,
            'threshold': 0.8
        }
        self.image_filter = ImageFilter()
        self.image_filter.set_filter(initial_filter)
        self.cap = None
        self.is_running = False
        self.current_vector = (0, 0)  # Store the current direction vector

    def start(self):
        if self.camera_index.startswith("ip:"):
            _, ip, port = self.camera_index.split(":")
            self.cap, success = connect_ip_camera(ip, port)
        else:
            self.cap, success = initialize_camera(int(self.camera_index))
            
        if not success:
            raise ValueError(f"Failed to open camera {self.camera_index}")
            
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 1)
        self.is_running = True

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.state['drawing'] = True
            self.state['origin'] = [(x, y), (x, y)]
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.state.get('drawing', False):
                self.state['origin'][1] = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self.state['drawing'] = False
            self.state['origin'][1] = (x, y)

    def find_bright_region(self, frame):
        processed = self.image_filter.apply(frame)
        max_val = np.max(processed)
        brightness_threshold = int(max_val * self.state['threshold'])
        _, bright_mask = cv2.threshold(processed, brightness_threshold, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rect_center = self.get_rectangle_center(self.state['origin'])
        
        if not contours:
            return rect_center, (0, 0), bright_mask
        
        largest_contour = max(contours, key=cv2.contourArea)
        M = cv2.moments(largest_contour)
        
        if M["m00"] == 0:
            center_point = rect_center
        else:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            center_point = (cx, cy)
        
        if self.point_in_rectangle(center_point, self.state['origin']):
            return center_point, (0, 0), bright_mask
        
        dx = center_point[0] - rect_center[0]
        dy = center_point[1] - rect_center[1]
        magnitude = np.sqrt(dx*dx + dy*dy)
        
        direction_vector = (dx/magnitude, dy/magnitude) if magnitude > 0 else (0, 0)
        self.current_vector = direction_vector  # Store the vector
        return center_point, direction_vector, bright_mask

    def point_in_rectangle(self, point, rect):
        x, y = point
        (x1, y1), (x2, y2) = rect
        left, right = min(x1, x2), max(x1, x2)
        top, bottom = min(y1, y2), max(y1, y2)
        return left <= x <= right and top <= y <= bottom

    def get_rectangle_center(self, rect):
        (x1, y1), (x2, y2) = rect
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        return (center_x, center_y)

    def update(self):
        if not self.is_running or not self.cap:
            return False

        ret, frame = self.cap.read()
        if not ret:
            return False

        center_point, direction, mask = self.find_bright_region(frame)
        
        display_frame = frame
        if self.state['show_filtered']:
            filtered_frame = self.image_filter.apply(frame)
            display_frame = cv2.cvtColor(filtered_frame, cv2.COLOR_GRAY2BGR)
            
            texts = [
                f"Vector: ({direction[0]:.2f}, {direction[1]:.2f})",
                f"Filter: {self.image_filter.get_current_filter()}",
                f"Threshold: {self.state['threshold']:.2f}"
            ]
            
            for i, text in enumerate(texts):
                cv2.putText(display_frame, text, (10, 30 + i*30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.rectangle(display_frame, self.state['origin'][0], self.state['origin'][1], (0, 0, 255), 2)
        rect_center = self.get_rectangle_center(self.state['origin'])
        cv2.drawMarker(display_frame, rect_center, (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
        cv2.drawMarker(display_frame, center_point, (0, 255, 0), cv2.MARKER_CROSS, 20, 2)
        
        vector_scale = 100
        vector_end = (
            int(rect_center[0] + direction[0] * vector_scale),
            int(rect_center[1] + direction[1] * vector_scale)
        )
        cv2.arrowedLine(display_frame, rect_center, vector_end, (255, 0, 0), 2)
        
        cv2.imshow(self.window_name, display_frame)
        
        if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
            return False
            
        key = cv2.waitKeyEx(1)
        if key == ord('q'):
            return False
        elif key == ord('f'):
            self.state['show_filtered'] = not self.state['show_filtered']
        elif key in [81, 2424832]:  # Left arrow
            self.image_filter.prev_filter()
        elif key in [83, 2555904]:  # Right arrow
            self.image_filter.next_filter()
        elif key in [82, 2621440]:  # Down arrow
            self.state['threshold'] = min(1.0, self.state['threshold'] - 0.05)
        elif key in [84, 2490368]:  # Up arrow
            self.state['threshold'] = max(0.0, self.state['threshold'] + 0.05)
        
        return True

    def stop(self):
        self.is_running = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

    def get_vector(self):
        """Get the current direction vector"""
        return self.current_vector

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--camera-index', type=str, default="0",
                       help='Index of the camera to use or ip:address:port for IP camera')
    parser.add_argument('--filter', type=str, default="None",
                       help='Initial filter to apply')
    args = parser.parse_args()
    
    detector = BrightnessDetector(args.camera_index, args.filter)
    detector.start()
    
    while detector.update():
        pass
    
    detector.stop()

if __name__ == "__main__":
    main() 