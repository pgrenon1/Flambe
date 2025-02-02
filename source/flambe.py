import socketio
import threading
import tkinter as tk
from tkinter import ttk
from ip_camera_dialog import IPCameraDialog
from brightness_detector import BrightnessDetector
from dataclasses import dataclass
from datetime import datetime
import multiprocessing
from flask import Flask
from cv2_enumerate_cameras import enumerate_cameras
import cv2
import sys
import logging
import os
from logging_config import setup_module_logger
import argparse

@dataclass
class Connection:
    sid: str
    connected_at: datetime
    ip: str
    user_agent: str
    http_version: str
    path: str
    query_string: str
    
def setup_logging():
    """Setup logging configuration"""
    # Get the executable's directory or current directory
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    log_file = os.path.join(app_dir, 'flambe.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Create logger
    logger = logging.getLogger('flambe')
    return logger

class FlambeApp:
    def __init__(self, root, ip_camera_args=None):
        self.logger = setup_module_logger('flambe')
        self.logger.info("Starting Flambe application")
        
        # Store IP camera args for later use
        self.ip_camera_args = ip_camera_args
        if ip_camera_args:
            self.logger.info(f"IP camera args provided: {ip_camera_args}")
        
        if hasattr(sys, '_MEIPASS'):
            self.logger.info("Running as frozen executable")
            multiprocessing.freeze_support()
            multiprocessing.set_start_method('spawn', force=True)
        
        self.setup_window(root)
        self.setup_state()
        self.setup_ui()
    
    def setup_window(self, root):
        """Initialize the main window"""
        self.root = root
        self.root.title("flambe Launcher")
        self.root.minsize(250, 250)
        
        # Set icon (cross-platform)
        try:
            # Windows
            self.root.iconbitmap('./assets/fire.ico')
        except:
            try:
                # Linux/Unix
                icon_img = tk.PhotoImage(file='./assets/fire.png')
                self.root.iconphoto(True, icon_img)
            except:
                self.logger.warning("Could not load application icon")
        
        # Create main frame
        self.frame = tk.Frame(root, padx=20, pady=20)
        self.frame.place(relx=0.5, rely=0.5, anchor='center')
        self.resize_window_to_content()
    
    def setup_state(self):
        """Initialize application state"""
        self.detector = None
        self.update_id = None
        self.detector_process = None
        self.command_queue = multiprocessing.JoinableQueue()
        self.vector_queue = multiprocessing.Queue()
        self.detector_running = False
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setup_camera_selection()
        self.setup_server_config()
        self.setup_buttons()
        self.resize_window_to_content()
        
        # Disable UI and start camera detection
        self.set_ui_enabled(False)
        self.root.after(100, self.detect_cameras)
    
    def set_ui_enabled(self, enabled):
        """Enable or disable all UI elements"""
        state = "normal" if enabled else "disabled"
        # Camera selection
        self.selected_camera.configure(state="readonly" if enabled else "disabled")
        # Server config
        self.ip_entry.configure(state=state)
        self.port_entry.configure(state=state)
        # Buttons
        self.brightness_button.configure(state=state)
        self.server_button.configure(state=state)
    
    def setup_camera_selection(self):
        """Setup camera selection UI"""
        # Create camera config frame with title
        camera_frame = tk.LabelFrame(self.frame, text="Camera Configuration", padx=10, pady=5)
        camera_frame.pack(pady=10, fill="x")
        
        # Inner frame for camera selection
        self.camera_frame = tk.Frame(camera_frame)
        self.camera_frame.pack(fill="x")
        
        # Label
        label = tk.Label(self.camera_frame, text="Camera:")
        label.pack(side=tk.LEFT)
        
        # Combobox for camera selection
        self.selected_camera = ttk.Combobox(self.camera_frame, width=30, state="readonly")
        self.selected_camera.pack(side=tk.LEFT, padx=5, fill="x", expand=True)
        self.selected_camera.bind('<<ComboboxSelected>>', self.on_camera_change)
        
        # Custom camera index entry (initially hidden)
        self.custom_camera_frame = tk.Frame(camera_frame)  # Changed parent to camera_frame
        self.custom_camera_frame.pack(pady=(2, 0), fill="x")
        tk.Label(self.custom_camera_frame, text="Index:").pack(side=tk.LEFT)
        self.custom_camera_entry = ttk.Entry(self.custom_camera_frame, width=30)
        self.custom_camera_entry.pack(side=tk.LEFT, padx=5, fill="x", expand=True)
        self.custom_camera_entry.insert(0, "0")
        
        # Add validation for numbers only
        vcmd = (self.root.register(self.validate_camera_index), '%P')
        self.custom_camera_entry.configure(validate='key', validatecommand=vcmd)
        
        # Initially hide custom entry
        self.custom_camera_frame.pack_forget()
    
    def setup_server_config(self):
        """Setup server configuration UI"""
        self.server_running = False
        self.sio = None
        # Create server config frame
        server_frame = tk.LabelFrame(self.frame, text="Server Configuration", padx=10, pady=5)
        server_frame.pack(pady=10, fill="x")
        
        # IP Address entry
        ip_frame = tk.Frame(server_frame)
        ip_frame.pack(fill="x", pady=2)
        tk.Label(ip_frame, text="IP:").pack(side=tk.LEFT)
        self.ip_var = tk.StringVar(value="127.0.0.1")
        self.ip_entry = ttk.Entry(ip_frame, textvariable=self.ip_var)
        self.ip_entry.pack(side=tk.LEFT, padx=(5, 0), fill="x", expand=True)
        
        # Port entry
        port_frame = tk.Frame(server_frame)
        port_frame.pack(fill="x", pady=2)
        tk.Label(port_frame, text="Port:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value="12345")
        self.port_entry = ttk.Entry(port_frame, textvariable=self.port_var)
        self.port_entry.pack(side=tk.LEFT, padx=(5, 0), fill="x", expand=True)
        
        # Server status
        status_frame = tk.Frame(server_frame)
        status_frame.pack(fill="x", pady=5)
        tk.Label(status_frame, text="Status:").pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="Stopped")
        self.status_label = tk.Label(status_frame, textvariable=self.status_var, fg="red")
        self.status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Connection count
        conn_frame = tk.Frame(server_frame)
        conn_frame.pack(fill="x", pady=2)
        tk.Label(conn_frame, text="Connections:").pack(side=tk.LEFT)
        self.conn_var = tk.StringVar(value="0")
        tk.Label(conn_frame, textvariable=self.conn_var).pack(side=tk.LEFT, padx=(5, 0))
    
    def update_server_status(self):
        """Update the server status display"""
        if self.server_running:
            self.status_var.set("Running")
            self.status_label.config(fg="green")
        else:
            self.status_var.set("Stopped")
            self.status_label.config(fg="red")
        self.conn_var.set(str(len(self.connections)))
    
    def setup_buttons(self):
        """Setup control buttons"""
        button_frame = tk.Frame(self.frame)
        button_frame.pack(pady=10)
        
        # Brightness detection button
        self.brightness_button = tk.Button(
            button_frame,
            text="Start flambe",
            command=self.toggle_brightness_detection,
            width=20,
            height=2,
            font=('Arial', 12),
            fg="green"
        )
        self.brightness_button.pack(pady=5)
        
        # Calibrate button
        self.calibrate_button = tk.Button(
            button_frame,
            text="Calibrate",
            command=self.calibrate,
            width=20,
            height=2,
            font=('Arial', 12),
            state="disabled"  # Initially disabled
        )
        self.calibrate_button.pack(pady=5)
        
        # Server control button
        self.server_button = tk.Button(
            button_frame,
            text="Start Server",
            command=self.toggle_server,
            width=20,
            height=2,
            font=('Arial', 12),
            fg="green"
        )
        self.server_button.pack(pady=5)
    
    def start_brightness_detection(self):
        """Start brightness detection"""
        camera_arg = self.get_camera_index()
        
        try:
            # Create fresh queues
            self.command_queue = multiprocessing.JoinableQueue()
            self.vector_queue = multiprocessing.Queue()
            
            # Start detector in a separate process
            self.detector_process = multiprocessing.Process(
                target=BrightnessDetector.run_detector,
                args=(camera_arg, self.command_queue, self.vector_queue)
            )
            self.detector_process.start()
            
            self.detector_running = True
            self.brightness_button.config(text="Stop flambe", fg="red")
            self.update_detector()
        except Exception as e:
            self.logger.error(f"Error starting brightness detection: {e}")
            self.stop_brightness_detection()
    
    def stop_brightness_detection(self):
        """Stop brightness detection"""
        self.detector_running = False
        
        # Clean up process
        if self.detector_process is not None:
            self.detector_process.terminate()
            self.detector_process.join()
            self.detector_process = None
        
        # Clean up queues
        if self.command_queue is not None:
            self.command_queue.close()
            self.command_queue = None
        if self.vector_queue is not None:
            self.vector_queue.close()
            self.vector_queue = None
        
        self.brightness_button.config(text="Start flambe", fg="green")
        self.calibrate_button.config(state="disabled")
    
    def update_detector(self):
        """Check for updates from the detector process"""
        if not self.detector_running:
            return

        try:
            # Check for commands
            if not self.command_queue.empty():
                command = self.command_queue.get_nowait()
                if command == "STOP":
                    self.logger.info("Received STOP signal from detector")
                    self.stop_brightness_detection()
                    return

            # Check for vectors
            while not self.vector_queue.empty():
                vector = self.vector_queue.get_nowait()
                if self.sio:
                    self.logger.info(f"Sending vector: ({vector[0]}, {vector[1]})")
                    self.sio.emit('vector', {'x': vector[0], 'y': vector[1]})
                    
        except Exception as e:
            self.logger.error(f"Error in update_detector: {e}")
            self.stop_brightness_detection()
            return

        self.update_id = self.root.after(10, self.update_detector)
    
    def toggle_brightness_detection(self):
        """Toggle brightness detection on/off"""
        if self.detector_running:
            self.stop_brightness_detection()
            self.calibrate_button.config(state="disabled")
        else:
            self.start_brightness_detection()
            self.calibrate_button.config(state="normal")
    
    def on_camera_change(self, event):
        """Handle camera selection change"""
        selection = self.selected_camera.get()
        if selection.startswith("ip:"):
            self.show_ip_camera_dialog()
            self.custom_camera_frame.pack_forget()
        elif selection.startswith("custom:"):
            self.custom_camera_frame.pack()
        else:
            self.custom_camera_frame.pack_forget()
    
    def show_ip_camera_dialog(self):
        """Show dialog for IP camera connection"""
        dialog = IPCameraDialog(self.root)
        if dialog.result:
            address, port = dialog.result
            self.selected_camera.set(f"ip:{address}:{port}")
    
    def resize_window_to_content(self):
        """Resize the main window to fit its content"""
        self.root.update_idletasks()
        
        frame_width = self.frame.winfo_reqwidth()
        frame_height = self.frame.winfo_reqheight()
        
        window_width = frame_width + 40
        window_height = frame_height + 40
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        position_x = (screen_width - window_width) // 2
        position_y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_brightness_detection()
        self.root.destroy()

    def stop_server(self):
        """Stop the socket server and clean up resources"""
        self.logger.info("Stopping server...")
        self.server_running = False
        
        try:
            self.disconnect_all_clients()
            self.shutdown_servers()
            self.cleanup_server_resources()
            self.reset_server_ui()
            self.update_server_status()
            self.logger.info("Server stopped successfully")
        except Exception as e:
            self.logger.error(f"Error stopping server: {e}", exc_info=True)
    
    def disconnect_all_clients(self):
        """Disconnect all connected Socket.IO clients"""
        try:
            if self.sio:
                self.logger.info(f"Disconnecting {len(self.connections)} clients")
                for sid in list(self.connections.keys()):
                    self.logger.info(f"Disconnecting client {sid}")
                    self.sio.disconnect(sid)
            self.logger.info("All clients disconnected")
        except Exception as e:
            self.logger.error(f"Error disconnecting clients: {e}", exc_info=True)
    
    def shutdown_servers(self):
        """Shutdown the web server"""
        try:
            if self.server is not None:
                self.logger.info("Shutting down web server")
                self.server.shutdown()
                self.logger.info("Web server shutdown complete")
        except Exception as e:
            self.logger.error(f"Error shutting down web server: {e}", exc_info=True)
    
    def cleanup_server_resources(self):
        """Clean up server-related resources"""
        try:
            if self.server_thread:
                self.logger.info("Waiting for server thread to finish")
                self.server_thread.join(timeout=1)
                if self.server_thread.is_alive():
                    self.logger.warning("Server thread did not finish within timeout")
            if self.sio:
                self.logger.info("Shutting down Socket.IO")
                self.sio.shutdown()
            self.sio = None
            self.app = None
            self.server = None
            self.server_thread = None
            self.logger.info("Server resources cleaned up")
        except Exception as e:
            self.logger.error(f"Error cleaning up server resources: {e}", exc_info=True)
    
    def reset_server_ui(self):
        """Reset UI elements to initial server-stopped state"""
        self.server_button.config(text="Start Server", fg="green")
        self.ip_entry.config(state="normal")
        self.port_entry.config(state="normal")
        self.connections = {}
        self.update_server_status()
    
    def start_server(self):
        """Initialize and start the socket server"""
        try:
            host = self.ip_var.get()
            port = int(self.port_var.get())
            
            self.logger.info(f"Starting server on {host}:{port}")
            self.setup_flask_app(host, port)
            self.start_server_thread()
            self.update_ui_for_server_start()
            self.update_server_status()
            self.logger.info("Server started successfully")
        except Exception as e:
            self.logger.error(f"Error starting server: {e}", exc_info=True)
            self.stop_server()
    
    def setup_flask_app(self, host, port):
        """Setup Flask and Socket.IO server"""
        try:
            flask_app = Flask(__name__)
            
            # Create Socket.IO server with logging configuration
            self.logger.info("Creating Socket.IO server")
            self.sio = socketio.Server(
                async_mode='threading',
                cors_allowed_origins='*',
                logger=False,  # Disable Socket.IO's default logging
                engineio_logger=False  # Disable Engine.IO's default logging
            )
            
            self.app = socketio.WSGIApp(self.sio, flask_app)
            
            self.connections = {}
            self.setup_socketio_handlers()
            self.setup_flask_routes(flask_app)
            
            from wsgiref.simple_server import make_server
            self.logger.info("Creating server instance")
            self.server = make_server(host, port, self.app)
            self.logger.info("Server instance created")
        except Exception as e:
            self.logger.error(f"Error in setup_flask_app: {e}", exc_info=True)
            raise
    
    def setup_socketio_handlers(self):
        """Setup Socket.IO event handlers"""
        @self.sio.event
        def connect(sid, environ):
            self.handle_client_connect(sid, environ)

        @self.sio.event
        def disconnect(sid):
            self.handle_client_disconnect(sid)
    
    def handle_client_connect(self, sid, environ):
        """Handle new client connection"""
        client_ip = environ.get('REMOTE_ADDR', 'unknown')
        user_agent = environ.get('HTTP_USER_AGENT', 'unknown')
        http_version = environ.get('SERVER_PROTOCOL', 'unknown')
        path = environ.get('PATH_INFO', 'unknown')
        query = environ.get('QUERY_STRING', '')
        
        self.logger.info(f"Client {sid} connected from {client_ip}")
        self.logger.info(f"User Agent: {user_agent}")
        
        self.connections[sid] = Connection(
            sid=sid,
            connected_at=datetime.now(),
            ip=client_ip,
            user_agent=user_agent,
            http_version=http_version,
            path=path,
            query_string=query
        )
        
        self.update_server_status()
        self.sio.emit('welcome', {'message': 'Welcome!'}, room=sid)
    
    def handle_client_disconnect(self, sid):
        """Handle client disconnection"""
        if sid in self.connections:
            conn = self.connections[sid]
            self.logger.info(f"Client {sid} disconnected (was connected from {conn.ip})")
            del self.connections[sid]
            self.update_server_status()
    
    def setup_flask_routes(self, flask_app):
        """Setup Flask routes"""
        @flask_app.route('/')
        def index():
            return 'flambe Server Running'
    
    def start_server_thread(self):
        """Start the server in a separate thread"""
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
    
    def update_ui_for_server_start(self):
        """Update UI elements for server start state"""
        self.server_running = True
        self.server_button.config(text="Stop Server", fg="red")
        self.ip_entry.config(state="disabled")
        self.port_entry.config(state="disabled")
    
    def toggle_server(self):
        """Toggle socket server on/off"""
        if self.server_running:
            self.stop_server()
        else:
            self.start_server()

    def detect_cameras(self):
        """Detect cameras and update UI"""
        try:
            self.cameras = enumerate_cameras(cv2.CAP_ANY)
            
            # Setup camera options
            self.camera_options = [(info.index, info.name) for info in self.cameras]
            self.camera_options.extend([
                ('ip', 'Connect IP Camera...'),
                ('custom', '...')
            ])
            
            # Update combobox values
            values = [f"{idx}: {name}" for idx, name in self.camera_options]
            self.selected_camera.configure(values=values)
            
            # Set default camera based on args or first available
            if self.ip_camera_args:
                ip, port = self.ip_camera_args
                self.selected_camera.set(f"ip:{ip}:{port}")
                self.custom_camera_frame.pack_forget()
            elif self.cameras:
                self.default_camera = values[0]
                self.selected_camera.set(self.default_camera)
                self.custom_camera_frame.pack_forget()
            else:
                self.logger.warning("No cameras detected")
                self.selected_camera.set("custom: ...")
                self.custom_camera_frame.pack()
                
        except Exception as e:
            self.logger.error(f"Error detecting cameras: {e}")
            self.selected_camera.set("custom: ...")
            self.custom_camera_frame.pack()
        
        self.set_ui_enabled(True)

    def validate_camera_index(self, value):
        """Validate camera index input to only allow numbers"""
        if value == "":
            return True
        try:
            int(value)
            return True
        except ValueError:
            return False

    def get_camera_index(self):
        """Get camera index from either combobox or custom entry"""
        camera_selection = self.selected_camera.get()
        if camera_selection.startswith("ip:"):
            return camera_selection
        elif camera_selection.startswith("custom:"):
            return self.custom_camera_entry.get()
        else:
            return camera_selection.split(':')[0]

    def calibrate(self):
        """Send calibrate command to detector"""
        if self.command_queue and self.detector_running:
            try:
                # Clear any existing commands first
                while not self.command_queue.empty():
                    _ = self.command_queue.get_nowait()
                    self.command_queue.task_done()
                # Send calibrate command and wait for completion
                self.command_queue.put("CALIBRATE")
                self.command_queue.join()  # Wait for command to be processed
                self.logger.info("Calibrate command completed")
            except Exception as e:
                self.logger.error(f"Error sending calibrate command: {e}")

def main():
    # Setup argument parser
    parser = argparse.ArgumentParser(description='Flambe Application')
    parser.add_argument('--ip', help='IP camera address and port (e.g. 192.168.0.123:8080). Default port is 8080 if not provided.')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Split IP and port if provided
    ip_camera_args = None
    if args.ip:
        try:
            ip, port = args.ip.split(':')
            ip_camera_args = (ip, port)
        except ValueError:
            # If no port provided, use default 8080
            ip_camera_args = (args.ip, '8080')
    
    root = tk.Tk()
    app = FlambeApp(root, ip_camera_args=ip_camera_args)
    root.protocol("WM_DELETE_WINDOW", app.cleanup)
    root.mainloop()

if __name__ == "__main__":
    main()
