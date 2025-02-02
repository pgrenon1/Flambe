import socketio
import threading
import multiprocessing
from flask import Flask
from datetime import datetime
from dataclasses import dataclass
from brightness_detector import BrightnessDetector
from logging_config import setup_module_logger

@dataclass
class Connection:
    sid: str
    connected_at: datetime
    ip: str
    user_agent: str
    http_version: str
    path: str
    query_string: str

class FlambeAppHeadless:
    def __init__(self, args):
        self.logger = setup_module_logger('flambe')
        self.logger.info("Starting Flambe in headless mode")
        
        # Initialize state
        self.detector_running = False
        self.server_running = False
        self.detector_process = None
        self.command_queue = None
        self.vector_queue = None
        self.sio = None
        self.server = None
        self.server_thread = None
        self.connections = {}
        
        try:
            # Start server first
            self.logger.info(f"Starting server on {args.server_ip}:{args.server_port}")
            self.start_server(args.server_ip, int(args.server_port))
            self.server_running = True
            
            # Then start detector
            camera_arg = "0"  # Default to first camera
            if args.camera_ip:
                try:
                    ip, port = args.camera_ip.split(':')
                    camera_arg = f"ip:{ip}:{port}"
                except ValueError:
                    camera_arg = f"ip:{args.camera_ip}:8080"
            
            self.logger.info(f"Starting detector with camera: {camera_arg}")
            self.start_detector(camera_arg)
            
            # Keep main thread alive and show status
            while True:
                import time
                self.logger.info(f"Server running: {self.server_running}, Detector running: {self.detector_running}, Connected clients: {len(self.connections)}")
                time.sleep(5)  # Status update every 5 seconds
                
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down...")
            self.stop_detector()
            self.stop_server()
        except Exception as e:
            self.logger.error(f"Error in headless mode: {e}")
            self.stop_detector()
            self.stop_server()

    def start_detector(self, camera_arg):
        """Start brightness detection"""
        try:
            # Create fresh queues
            self.command_queue = multiprocessing.JoinableQueue()
            self.vector_queue = multiprocessing.Queue()
            
            # Start detector in a separate process with headless=True
            self.detector_process = multiprocessing.Process(
                target=BrightnessDetector.run_detector,
                args=(camera_arg, self.command_queue, self.vector_queue, True)
            )
            self.detector_process.start()
            
            self.detector_running = True
            self.update_detector()
        except Exception as e:
            self.logger.error(f"Error starting brightness detection: {e}")
            self.stop_detector()

    def stop_detector(self):
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
                    self.stop_detector()
                    return

            # Check for vectors
            while not self.vector_queue.empty():
                vector = self.vector_queue.get_nowait()
                if self.sio:
                    self.logger.info(f"Sending vector: ({vector[0]}, {vector[1]})")
                    self.sio.emit('vector', {'x': vector[0], 'y': vector[1]})
                    
        except Exception as e:
            self.logger.error(f"Error in update_detector: {e}")
            self.stop_detector()
            return

        threading.Timer(0.01, self.update_detector).start()

    def start_server(self, host, port):
        """Initialize and start the socket server"""
        try:
            self.logger.info(f"Starting server on {host}:{port}")
            self.setup_flask_app(host, port)
            self.start_server_thread()
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
        
        self.sio.emit('welcome', {'message': 'Welcome!'}, room=sid)
    
    def handle_client_disconnect(self, sid):
        """Handle client disconnection"""
        if sid in self.connections:
            conn = self.connections[sid]
            self.logger.info(f"Client {sid} disconnected (was connected from {conn.ip})")
            del self.connections[sid]
    
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
    
    def stop_server(self):
        """Stop the socket server and clean up resources"""
        self.logger.info("Stopping server...")
        self.server_running = False
        
        try:
            self.disconnect_all_clients()
            self.shutdown_servers()
            self.cleanup_server_resources()
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