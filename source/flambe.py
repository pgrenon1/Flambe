import eventlet
import socketio
import eventlet.wsgi
import threading
import tkinter as tk
from tkinter import ttk
from ip_camera_dialog import IPCameraDialog
from brightness_detector import BrightnessDetector
from dataclasses import dataclass
from datetime import datetime
import multiprocessing
from flask import Flask
from werkzeug.serving import make_server
from cv2_enumerate_cameras import enumerate_cameras
import cv2
from logging_config import setup_module_logger
import argparse
import os
import configparser

@dataclass
class Connection:
    sid: str
    connected_at: datetime
    ip: str
    user_agent: str
    http_version: str
    path: str
    query_string: str
    
class FlambeApp:
    def __init__(self, root, camera_ip=None, server_ip=None, server_port=None):
        self.logger = setup_module_logger('flambe')
        self.logger.info("Starting Flambe application")
        self.camera_ip = camera_ip
        self.server_ip = server_ip
        self.server_port = server_port
        self.setup_window(root)
        self.setup_state()
        self.setup_ui()
    
    def setup_window(self, root):
        """Initialize the main window"""
        self.root = root
        self.root.title("Flambe Launcher")
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
                print("Warning: Could not load application icon")
        
        # Create main frame
        self.frame = tk.Frame(root, padx=0, pady=0)
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
        self.selected_camera = ttk.Combobox(self.camera_frame, state="readonly")
        self.selected_camera.pack(side=tk.LEFT, padx=5, fill="x", expand=True)
        self.selected_camera.bind('<<ComboboxSelected>>', self.on_camera_change)
        
        # Custom camera index entry (always visible)
        self.custom_camera_frame = tk.Frame(camera_frame)
        self.custom_camera_frame.pack(fill="x", pady=2)
        
        tk.Label(self.custom_camera_frame, text="Index:").pack(side=tk.LEFT)
        self.custom_camera_entry = ttk.Entry(self.custom_camera_frame)
        self.custom_camera_entry.pack(side=tk.LEFT, padx=(5, 0), fill="x", expand=True)
        
        # Add validation for numbers only
        vcmd = (self.root.register(self.validate_camera_index), '%P')
        self.custom_camera_entry.configure(validate='key', validatecommand=vcmd)
        
        # Initially disable custom entry
        self.custom_camera_entry.configure(state="disabled")
    
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
        self.ip_var = tk.StringVar(value="127.0.0.1" if self.server_ip is None else self.server_ip)
        self.ip_entry = ttk.Entry(ip_frame, textvariable=self.ip_var)
        self.ip_entry.pack(side=tk.LEFT, padx=(5, 0), fill="x", expand=True)
        
        # Port entry
        port_frame = tk.Frame(server_frame)
        port_frame.pack(fill="x", pady=2)
        tk.Label(port_frame, text="Port:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value="12345" if self.server_port is None else self.server_port)
        self.port_entry = ttk.Entry(port_frame, textvariable=self.port_var)
        self.port_entry.pack(side=tk.LEFT, padx=(5, 0), fill="x", expand=True)
        
        # Connection counter
        conn_frame = tk.Frame(server_frame)
        conn_frame.pack(fill="x", pady=2)
        tk.Label(conn_frame, text="Connections:").pack(side=tk.LEFT)
        self.conn_var = tk.StringVar(value="0")
        tk.Label(conn_frame, textvariable=self.conn_var).pack(side=tk.LEFT, padx=(5, 0))
        
        # Connection list
        conn_list_frame = tk.LabelFrame(server_frame, text="Active Connections", padx=5, pady=5)
        conn_list_frame.pack(fill="x", pady=(5, 0))
        self.conn_text = tk.Text(conn_list_frame, height=4, width=40)
        self.conn_text.configure(state='disabled')  # Make it read-only
        self.conn_text.pack(fill="x")
    
    def update_connection_display(self):
        """Update the connection list display"""
        self.conn_text.configure(state='normal')  # Temporarily enable for update
        self.conn_text.delete(1.0, tk.END)
        for conn in self.connections.values():
            time_str = conn.connected_at.strftime("%H:%M:%S")
            self.conn_text.insert(tk.END, f"IP: {conn.ip}\n")
            self.conn_text.insert(tk.END, f"Connected at: {time_str}\n")
            self.conn_text.insert(tk.END, f"Browser: {conn.user_agent}\n")
            self.conn_text.insert(tk.END, f"HTTP Version: {conn.http_version}\n")
            self.conn_text.insert(tk.END, f"Path: {conn.path}\n")
            if conn.query_string:
                self.conn_text.insert(tk.END, f"Query: {conn.query_string}\n")
            self.conn_text.insert(tk.END, "-" * 40 + "\n")
        self.conn_text.configure(state='disabled')  # Make read-only again
        self.conn_var.set(str(len(self.connections)))
    
    def setup_buttons(self):
        """Setup control buttons"""
        button_frame = tk.Frame(self.frame)
        button_frame.pack(pady=10)
        
        # Brightness detection button
        self.brightness_button = tk.Button(
            button_frame,
            text="Start Flambe",
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
        
        # Add save config button
        self.save_config_button = tk.Button(
            button_frame,
            text="Save Config",
            command=self.save_configuration,
            width=20,
            height=2,
            font=('Arial', 12)
        )
        self.save_config_button.pack(pady=5)
    
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
            self.brightness_button.config(text="Stop Flambe", fg="red")
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
        
        self.brightness_button.config(text="Start Flambe", fg="green")
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
            self.custom_camera_entry.configure(state="disabled")
        elif selection.startswith("custom:"):
            self.custom_camera_entry.configure(state="normal")
        else:
            self.custom_camera_entry.configure(state="disabled")
    
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
        
        self.disconnect_all_clients()
        self.shutdown_servers()
        self.cleanup_server_resources()
        self.reset_server_ui()
        self.logger.info("Server stopped")
    
    def disconnect_all_clients(self):
        """Disconnect all connected Socket.IO clients"""
        if self.sio:
            for sid in list(self.connections.keys()):
                self.sio.disconnect(sid)
            self.sio.shutdown()
    
    def shutdown_servers(self):
        """Shutdown the web server"""
        if self.server is not None:
            self.server.shutdown()
    
    def cleanup_server_resources(self):
        """Clean up server-related resources"""
        if self.server_thread:
            self.server_thread.join(timeout=1)
        self.sio = None
        self.app = None
        self.server_thread = None
    
    def reset_server_ui(self):
        """Reset UI elements to initial server-stopped state"""
        self.server_button.config(text="Start Server", fg="green")
        self.ip_entry.config(state="normal")
        self.port_entry.config(state="normal")
        self.connections = {}
        self.update_connection_display()
    
    def start_server(self):
        """Initialize and start the socket server"""
        host = self.ip_var.get()
        port = int(self.port_var.get())
        
        self.setup_flask_app(host, port)
        self.start_server_thread()
        self.update_ui_for_server_start()
        self.logger.info("Server is running...")
    
    def setup_flask_app(self, host, port):
        """Setup Flask and Socket.IO server"""
        flask_app = Flask(__name__)
        self.logger.info(f"Setting up Flask app on {host}:{port}")
        
        self.sio = socketio.Server(async_mode='threading')
        self.logger.info("Created Socket.IO server with threading mode")
        
        self.app = socketio.WSGIApp(self.sio, flask_app)
        self.logger.info("Created WSGI app")
        
        self.connections = {}
        self.setup_socketio_handlers()
        self.setup_flask_routes(flask_app)
        
        self.server = make_server(host, port, self.app)
        self.logger.info(f"Server created and bound to {host}:{port}")
    
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
        
        self.update_connection_display()
        self.sio.emit('welcome', {'message': 'Welcome!'}, room=sid)
    
    def handle_client_disconnect(self, sid):
        """Handle client disconnection"""
        if sid in self.connections:
            conn = self.connections[sid]
            self.logger.info(f"Client {sid} disconnected (was connected from {conn.ip})")
            del self.connections[sid]
            self.update_connection_display()
    
    def setup_flask_routes(self, flask_app):
        """Setup Flask routes"""
        @flask_app.route('/')
        def index():
            return 'Flambe Server Running'
    
    def start_server_thread(self):
        """Start the server in a separate thread"""
        self.logger.info("Starting server thread...")
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.logger.info("Server thread started")
    
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
            
            # Set default camera based on arguments
            if self.camera_ip:
                self.logger.info(f"Using provided IP camera: {self.camera_ip}")
                self.selected_camera.set(f"ip:{self.camera_ip}")
            elif self.cameras:
                self.default_camera = values[0]
                self.selected_camera.set(self.default_camera)
                self.custom_camera_entry.configure(state="disabled")
            else:
                self.logger.warning("No cameras detected")
                self.selected_camera.set("custom: ...")
                self.custom_camera_entry.configure(state="normal")
                
        except Exception as e:
            self.logger.error(f"Error detecting cameras: {e}")
            self.selected_camera.set("custom: ...")
            self.custom_camera_entry.configure(state="normal")
        
        self.set_ui_enabled(True)

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

    def save_configuration(self):
        """Save current configuration to file"""
        try:
            config = configparser.ConfigParser()
            
            # Server section
            config['Server'] = {
                'ip': self.ip_var.get(),
                'port': self.port_var.get()
            }
            
            # Camera section
            camera_selection = self.selected_camera.get()
            config['Camera'] = {
                'camera_ip': '',
                'camera_port': '8080',
                'camera_index': ''
            }
            
            # Parse camera selection to populate correct fields
            if camera_selection.startswith("ip:"):
                # Format is "ip:192.168.0.197:8080"
                _, ip, port = camera_selection.split(":")
                config['Camera']['camera_ip'] = ip
                config['Camera']['camera_port'] = port
            elif not camera_selection.startswith("custom:"):
                # Regular camera index
                config['Camera']['camera_index'] = camera_selection.split(':')[0]
            
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
            with open(config_path, 'w') as f:
                config.write(f)
            
            self.logger.info(f"Configuration saved to {config_path}")
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")

def main():
    # Setup logger first
    logger = setup_module_logger('flambe')

    # Setup argument parser
    parser = argparse.ArgumentParser(description='Flambe Application')
    parser.add_argument('--config', 
                       help='Path to config file (defaults to config.ini if no path given)',
                       nargs='?',
                       const=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini'))
    
    # Parse arguments
    args = parser.parse_args()
    logger.info(f"Parsed arguments: config={args.config}")
    
    # Load configuration only if --config was specified
    config = configparser.ConfigParser()
    camera_ip = None
    server_ip = None
    server_port = None
    
    if args.config:
        try:
            if not os.path.exists(args.config):
                raise FileNotFoundError(f"Config file not found: {args.config}")
            
            logger.info(f"Reading config from: {args.config}")
            config.read(args.config)
            
            # Log config sections
            logger.info(f"Found config sections: {config.sections()}")
            
            if 'Camera' in config:
                logger.info("Processing Camera section")
                camera_ip = config['Camera'].get('camera_ip')
                camera_port = config['Camera'].get('camera_port', '8080')
                if camera_ip:
                    camera_ip = f"{camera_ip}:{camera_port}"
                    logger.info(f"Found camera IP configuration: {camera_ip}")
                else:
                    camera_index = config['Camera'].get('camera_index')
                    if camera_index:
                        camera_ip = camera_index
                        logger.info(f"Found camera index configuration: {camera_index}")
                    else:
                        logger.info("No camera configuration found")
            
            if 'Server' in config:
                logger.info("Processing Server section")
                server_ip = config['Server'].get('ip')
                server_port = config['Server'].get('port')
                logger.info(f"Found server configuration - IP: {server_ip}, Port: {server_port}")
            
        except Exception as e:
            logger.error(f"Error reading config file: {e}", exc_info=True)
    else:
        logger.info("No config file specified, using default values")
    
    logger.info(f"Final configuration - Camera IP: {camera_ip}, Server IP: {server_ip}, Server Port: {server_port}")
    
    root = tk.Tk()
    app = FlambeApp(root, camera_ip=camera_ip, server_ip=server_ip, server_port=server_port)
    root.protocol("WM_DELETE_WINDOW", app.cleanup)
    root.mainloop()

if __name__ == "__main__":
    main()
