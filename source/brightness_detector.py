import cv2
import numpy as np
from camera_utils import initialize_camera, connect_ip_camera
import multiprocessing
import ctypes
import os
from logging_config import setup_module_logger

logger = setup_module_logger('brightness_detector')

def set_window_icon(window_name, icon_path):
    """Set the icon for an OpenCV window using Win32 API"""
    try:
        if os.name == 'nt':  # Windows
            hwnd = ctypes.windll.user32.FindWindowW(None, window_name)
            if hwnd != 0:  # If window found
                # Load the icon
                icon_handle = ctypes.windll.user32.LoadImageW(
                    0, icon_path, 1, 0, 0, 0x00000010 | 0x00000040)
                if icon_handle:
                    # Set the icon
                    ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, icon_handle)  # SETICON
                    ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, icon_handle)  # SETICON
        elif os.name == 'posix':  # Linux/Unix/macOS
            # On Linux/Unix, OpenCV windows don't support custom icons directly
            # Could potentially use X11/Xlib but this requires additional dependencies
            pass
        else:
            logger.error(f"Unsupported operating system: {os.name}")
    except Exception as e:
        logger.error(f"Failed to set window icon: {e}")

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

class BrightnessDetector:
    @staticmethod
    def run_detector(camera_arg, command_queue, vector_queue):
        try:
            logger.info(f"Starting detector with camera {camera_arg}")
            detector = BrightnessDetector(camera_arg, command_queue, vector_queue)
            detector.run()
        except Exception as e:
            logger.error(f"Detector error: {e}", exc_info=True)
        finally:
            logger.info("Detector stopping")
            try:
                command_queue.put("STOP", block=False)
            except:
                pass

    def __init__(self, camera_arg, command_queue, vector_queue):
        logger.info("Initializing BrightnessDetector")
        self.setup_state(camera_arg, command_queue, vector_queue)
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self.on_mouse)
        # icon_path = os.path.abspath('./assets/fire.ico')
        # set_window_icon(self.window_name, icon_path)
        self.setup_camera()

    def setup_state(self, camera_arg, command_queue, vector_queue):
        self.camera_arg = camera_arg
        self.command_queue = command_queue
        self.vector_queue = vector_queue
        self.window_name = "Flambe"
        self.image_filter = ImageFilter()
        self.state = {
            'center': None,
            'radius': 0,
            'drawing': False,
            'show_filtered': False,
            'threshold': 0.8
        }
        self.is_running = True

    def setup_camera(self):
        if isinstance(self.camera_arg, str) and self.camera_arg.startswith("ip:"):
            _, ip, port = self.camera_arg.split(":")
            self.cap, success = connect_ip_camera(ip, port)
        else:
            self.cap, success = initialize_camera(int(self.camera_arg))
        
        if not success:
            raise ValueError(f"Failed to open camera {self.camera_arg}")
        
        # Get camera resolution
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Configure window properties
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_ASPECT_RATIO, cv2.WINDOW_KEEPRATIO)
        cv2.resizeWindow(self.window_name, self.frame_width, self.frame_height)

    def on_mouse(self, event, x, y, flags, param):
        # Scale coordinates back to original frame size
        x = int(x * getattr(self, 'scale_x', 1.0))
        y = int(y * getattr(self, 'scale_y', 1.0))
        
        if event == cv2.EVENT_LBUTTONDOWN:
            self.state['drawing'] = True
            self.state['center'] = (x, y)
            self.state['radius'] = 0
        elif event == cv2.EVENT_MOUSEMOVE and self.state['drawing']:
            if self.state['center']:
                dx = x - self.state['center'][0]
                dy = y - self.state['center'][1]
                self.state['radius'] = int(np.sqrt(dx*dx + dy*dy))
        elif event == cv2.EVENT_LBUTTONUP:
            self.state['drawing'] = False

    def handle_key(self, key):
        if key == ord('q'):
            self.command_queue.put("STOP")
            return False
        elif key == ord('f'):
            self.state['show_filtered'] = not self.state['show_filtered']
        elif key == ord('s'):
            self.calibrate(self.cap.read()[1])
        elif key in [81, 2424832, 63234]:  # Left arrow (including Linux codes)
            self.image_filter.prev_filter()
        elif key in [83, 2555904, 63235]:  # Right arrow
            self.image_filter.next_filter()
        elif key in [82, 2621440, 63233]:  # Down arrow
            self.state['threshold'] = max(0.0, self.state['threshold'] - 0.05)
        elif key in [84, 2490368, 63232]:  # Up arrow
            self.state['threshold'] = min(1.0, self.state['threshold'] + 0.05)
        return True

    def find_bright_region(self, frame):
        """Find the brightest region in the frame using moments"""            
        processed = self.image_filter.apply(frame)
        processed = cv2.normalize(processed, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
        
        max_val = np.max(processed)
        threshold = int(max_val * self.state['threshold'])
        _, bright_mask = cv2.threshold(processed, threshold, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return bright_mask, None
        
        largest_contour = max(contours, key=cv2.contourArea)
        moments = cv2.moments(largest_contour)
        
        if moments["m00"] == 0:
            return bright_mask, None

        return bright_mask, moments

    def get_bright_point(self, moments):
        """Calculate bright point from moments"""
        if moments is None:
            return None
        return (
            int(moments["m10"] / moments["m00"]),
            int(moments["m01"] / moments["m00"])
        )

    def draw_overlay(self, frame, bright_point):
        display = frame.copy()
        
        if self.state['center'] is not None:
            # Draw circle
            cv2.circle(display, self.state['center'], self.state['radius'], (0, 0, 255), 2)
            
            # Draw center cross
            cv2.drawMarker(display, self.state['center'], (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
            
            # Draw bright point and arrow if applicable
            if bright_point is not None:
                cv2.drawMarker(display, bright_point, (0, 255, 0), cv2.MARKER_CROSS, 20, 2)
                
                # Calculate vector and draw arrow if outside circle
                if not self.point_in_circle(bright_point):
                    cv2.arrowedLine(display, self.state['center'], bright_point, (255, 0, 0), 2)
        
        return display

    def point_in_circle(self, point):
        if self.state['center'] is None:
            return False
            
        px, py = point
        cx, cy = self.state['center']
        dx = px - cx
        dy = py - cy
        distance = np.sqrt(dx*dx + dy*dy)
        
        return distance <= self.state['radius']

    def run(self):
        logger.info("Starting detector main loop")
        while self.is_running:
            try:
                # Check if window was closed
                if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                    self.command_queue.put("STOP")
                    break

                # Read frame from camera
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    logger.error("Failed to read frame from camera")
                    break

                if self.command_queue and not self.command_queue.qsize() == 0:
                    command = self.command_queue.get()
                    logger.info(f"Processing command: {command}")
                    if command == "CALIBRATE":
                        self.calibrate(frame)
                        self.command_queue.task_done()
                    elif command == "STOP":
                        self.is_running = False
                        self.command_queue.task_done()
                        break
                
                # Process frame and get moments
                processed, moments = self.find_bright_region(frame)
                
                # Get bright point from moments
                bright_point = self.get_bright_point(moments)
                
                # Calculate vector from bright point
                current_vector = self.calculate_vector(bright_point)
                
                # Only send vector if we have a calibrated region
                if self.vector_queue and self.state['center'] is not None:
                    self.vector_queue.put(current_vector)
                
                # Prepare and show display
                display = self.prepare_display(frame, processed, bright_point, current_vector, moments)
                cv2.imshow(self.window_name, display)

                # Handle keyboard input
                key = cv2.waitKeyEx(1) if os.name == 'nt' else cv2.waitKey(1)
                if key != -1 and not self.handle_key(key):
                    break

            except Exception as e:
                logger.error(f"Error in detector loop: {e}", exc_info=True)
                break

        logger.info("Detector main loop ended")
        self.cleanup()

    def calculate_vector(self, bright_point):
        """Calculate the current vector based on bright point position"""
        if not bright_point or not self.state['center']:
            return (0, 0)
        
        dx = bright_point[0] - self.state['center'][0]
        dy = bright_point[1] - self.state['center'][1]
        
        return (0, 0) if self.point_in_circle(bright_point) else (dx, dy)

    def prepare_display(self, frame, processed, bright_point, current_vector, moments=None):
        """Prepare the display frame with all overlays"""
        if self.state['show_filtered'] and processed is not None:
            display = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
            self.add_info_overlay(display, current_vector, moments)
        else:
            display = frame.copy()
        
        display = self.draw_overlay(display, bright_point)
        
        # Get current window size
        rect = cv2.getWindowImageRect(self.window_name)
        if rect is None:
            return display
        
        # Scale coordinates to match original frame size
        self.scale_x = self.frame_width / rect[2]
        self.scale_y = self.frame_height / rect[3]
        
        # Resize display to window size
        return cv2.resize(display, (rect[2], rect[3]))

    def add_info_overlay(self, display, current_vector, moments=None):
        """Add text overlay with current settings and vector"""
        texts = [
            f"Filter: {self.image_filter.get_current_filter()}",
            f"Threshold: {self.state['threshold']:.2f}",
            f"Vector: ({current_vector[0]}, {current_vector[1]})"
        ]
        
        if moments:
            texts.extend([
                f"Area: {moments['m00']:.0f}",
                f"Centroid: ({int(moments['m10']/moments['m00'])}, {int(moments['m01']/moments['m00'])})"
            ])
        
        for i, text in enumerate(texts):
            cv2.putText(display, text, 
                       (10, 30 + i*30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 
                       1, (0, 255, 0), 2)

    def cleanup(self):
        """Clean up resources"""
        if self.cap:
            self.cap.release()
        cv2.destroyWindow(self.window_name)
        self.is_running = False

    def calibrate(self, frame):
        """Automatically create circle around brightest region using moments"""
        try:
            processed, moments = self.find_bright_region(frame)
            if moments is None:
                logger.error("No bright regions found")
                return
            
            bright_point = self.get_bright_point(moments)
            if bright_point is None:
                logger.error("Invalid moments")
                return
            
            # Calculate radius based on contour area
            area = moments["m00"]  # area is m00 moment
            radius = int(np.sqrt(area / np.pi))
            
            # Update state
            self.state['center'] = bright_point
            self.state['radius'] = radius
            
            logger.info(f"Calibrated at {bright_point} with radius {radius}")
            
        except Exception as e:
            logger.error(f"Error in calibrate: {e}")

def main():
    # For testing
    signal_queue = multiprocessing.Queue()
    vector_queue = multiprocessing.Queue()
    detector = BrightnessDetector(0, signal_queue, vector_queue)
    detector.run()

if __name__ == "__main__":
    main()
