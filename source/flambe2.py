import cv2
import numpy as np
import configparser
import logging
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] - %(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('flambe2.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FlambeServer(BaseHTTPRequestHandler):
    """Simple HTTP server to serve the current vector and handle commands"""
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            vector = self.server.get_vector()
            response = {"vector": vector}
            logger.info(f"Sending vector: {vector}")
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/command':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            command = json.loads(post_data.decode('utf-8'))
            
            response = {"status": "ok"}
            
            if command.get('action') == 'calibrate':
                logger.info("Received calibration command from web interface")
                self.server.flambe.calibrate()
            
            elif command.get('action') == 'toggle_filter':
                current = self.server.flambe.config['display']['show_filtered'].lower() == 'true'
                new_value = str(not current).lower()
                self.server.flambe.config['display']['show_filtered'] = new_value
                response['show_filtered'] = new_value == 'true'
                logger.info(f"Toggled filter view to {new_value}")
            
            elif command.get('action') == 'threshold_up':
                self.server.flambe.calibration['threshold'] = min(
                    1.0, 
                    self.server.flambe.calibration['threshold'] + 0.05
                )
                response['threshold'] = self.server.flambe.calibration['threshold']
                logger.info(f"Increased threshold to {self.server.flambe.calibration['threshold']:.2f}")
            
            elif command.get('action') == 'threshold_down':
                self.server.flambe.calibration['threshold'] = max(
                    0.0, 
                    self.server.flambe.calibration['threshold'] - 0.05
                )
                response['threshold'] = self.server.flambe.calibration['threshold']
                logger.info(f"Decreased threshold to {self.server.flambe.calibration['threshold']:.2f}")
            
            else:
                self.send_error(400, "Unknown command")
                return
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        return  # Suppress logging of HTTP requests

class Flambe:
    def __init__(self, config_path='config.ini'):
        self.load_config(config_path)
        self.current_vector = (0, 0)
        self.calibration = {
            'center': None,
            'radius': 50,  # Default radius
            'threshold': 0.8
        }
        
        # Initialize camera if enabled
        self.cap = None
        if self.config['camera']['enabled'].lower() == 'true':
            self.setup_camera()
        
        # Start HTTP server in a separate thread because we need it running alongside the main loop
        self.start_server()

    def load_config(self, config_path):
        """Load configuration from config.ini"""
        config = configparser.ConfigParser()
        config.read(config_path)
        
        self.config = {
            'camera': {
                'enabled': config.get('Camera', 'enabled', fallback='false'),
                'index': config.getint('Camera', 'index', fallback=0),
            },
            'display': {
                'enabled': config.get('Display', 'enabled', fallback='false'),
                'show_filtered': config.get('Display', 'show_filtered', fallback='true'),
                'show_vectors': config.get('Display', 'show_vectors', fallback='true')
            },
            'server': {
                'host': config.get('Server', 'host', fallback='localhost'),
                'port': config.getint('Server', 'port', fallback=8000)
            }
        }

    def setup_camera(self):
        """Initialize the camera"""
        try:
            self.cap = cv2.VideoCapture(self.config['camera']['index'])
            if not self.cap.isOpened():
                raise Exception(f"Failed to open camera {self.config['camera']['index']}")
            logger.info(f"Camera initialized successfully")
        except Exception as e:
            logger.error(f"Camera initialization failed: {e}")
            self.cap = None

    def start_server(self):
        """Start the HTTP server in a separate thread"""
        def run_server():
            server_address = (
                self.config['server']['host'],
                self.config['server']['port']
            )
            httpd = HTTPServer(server_address, FlambeServer)
            httpd.get_vector = lambda: self.current_vector
            httpd.flambe = self  # Give the server access to this Flambe instance
            logger.info(f"Server started at http://{server_address[0]}:{server_address[1]}")
            httpd.serve_forever()

        self.server_thread = Thread(target=run_server, daemon=True)
        self.server_thread.start()

    def find_bright_region(self, frame):
        """Process frame to find the brightest region"""
        # Convert to grayscale and apply Gaussian blur
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        processed = cv2.GaussianBlur(gray, (11, 11), 0)
        processed = cv2.normalize(processed, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
        
        max_val = np.max(processed)
        threshold = int(max_val * self.calibration['threshold'])
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

    def calculate_vector(self, bright_point):
        """Calculate vector from center to bright point"""
        if not bright_point or not self.calibration['center']:
            return (0, 0)
        
        dx = bright_point[0] - self.calibration['center'][0]
        dy = bright_point[1] - self.calibration['center'][1]
        
        # Check if point is within calibration circle
        distance = np.sqrt(dx*dx + dy*dy)
        if distance <= self.calibration['radius']:
            return (0, 0)
        
        return (dx, dy)

    def calibrate(self):
        """Force calibration with current bright point"""
        if self.current_bright_point is not None:
            self.calibration['center'] = self.current_bright_point
            logger.info(f"Web interface triggered calibration to point {self.current_bright_point}")

    def run(self):
        """Main loop"""
        try:
            while True:
                if self.cap is None:
                    # If no camera, use a black frame
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                else:
                    ret, frame = self.cap.read()
                    if not ret:
                        logger.error("Failed to read frame")
                        break

                # Process frame
                processed, moments = self.find_bright_region(frame)
                bright_point = self.get_bright_point(moments)
                self.current_bright_point = bright_point  # Store current bright point
                
                # Auto-calibrate if not calibrated
                if self.calibration['center'] is None and bright_point is not None:
                    self.calibration['center'] = bright_point
                    logger.info(f"Auto-calibrated to point {bright_point}")

                # Update current vector
                self.current_vector = self.calculate_vector(bright_point)

                # Display if enabled
                if self.config['display']['enabled'].lower() == 'true':
                    self.display_frame(frame, processed, bright_point)

                # Handle keyboard input if display is enabled
                if self.config['display']['enabled'].lower() == 'true':
                    key = cv2.waitKeyEx(1) if os.name == 'nt' else cv2.waitKey(1)
                    if key == ord('q'):
                        break
                    elif key == ord('f'):
                        self.config['display']['show_filtered'] = str(
                            not self.config['display']['show_filtered'].lower() == 'true'
                        ).lower()
                    elif key == ord('v'):
                        self.config['display']['show_vectors'] = str(
                            not self.config['display']['show_vectors'].lower() == 'true'
                        ).lower()
                    elif key == ord('c'):
                        if bright_point is not None:
                            self.calibration['center'] = bright_point
                            logger.info(f"Manually calibrated to point {bright_point}")
                    elif key in [84, 2621440, 63233]:  # Down arrow (including Linux codes)
                        self.calibration['threshold'] = max(0.0, self.calibration['threshold'] - 0.05)
                        logger.debug(f"Threshold decreased to {self.calibration['threshold']:.2f}")
                    elif key in [82, 2490368, 63232]:  # Up arrow
                        self.calibration['threshold'] = min(1.0, self.calibration['threshold'] + 0.05)
                        logger.debug(f"Threshold increased to {self.calibration['threshold']:.2f}")

        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.cleanup()

    def display_frame(self, frame, processed, bright_point):
        """Display the frame with overlays"""
        # Choose base display image based on filter setting
        if self.config['display']['show_filtered'].lower() == 'true':
            display = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
        else:
            display = frame.copy()
        
        # Draw vector visualization if enabled
        if self.config['display']['show_vectors'].lower() == 'true':
            # Draw calibration circle and markers
            if self.calibration['center']:
                cv2.circle(display, self.calibration['center'], 
                          self.calibration['radius'], (0, 0, 255), 2)
                cv2.drawMarker(display, self.calibration['center'], 
                             (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
            
            if bright_point:
                cv2.drawMarker(display, bright_point, 
                             (0, 255, 0), cv2.MARKER_CROSS, 20, 2)
        
        # Add text overlay
        cv2.putText(display, f"Vector: {self.current_vector}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Show display controls and current threshold
        cv2.putText(display, f"Threshold: {self.calibration['threshold']:.2f}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display, "F: Toggle Filtered View", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display, "V: Toggle Vectors", (10, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display, "C: Calibrate", (10, 150),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display, "Up/Down: Adjust Threshold", (10, 180),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display, "Q: Quit", (10, 210),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow("Flambe2", display)

    def cleanup(self):
        """Cleanup resources"""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

def main():
    flambe = Flambe()
    flambe.run()

if __name__ == "__main__":
    main() 