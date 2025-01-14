import socketio
import threading
from wsgiref.simple_server import make_server

class SocketServer:
    def __init__(self, host='127.0.0.1', port=12345):
        # Create Socket.IO server
        self.sio = socketio.Server()
        self.app = socketio.WSGIApp(self.sio)
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        
        # Setup event handlers
        @self.sio.event
        def connect(sid, environ):
            print(f"Client {sid} connected")
            self.sio.emit('welcome', {'message': 'Welcome to the server!'}, room=sid)
            
        @self.sio.event
        def disconnect(sid):
            print(f"Client {sid} disconnected")
    
    def start(self):
        """Start the socket server in a new thread"""
        print(f"Starting server on {self.host}:{self.port}")
        print("Spawning server thread...")
        self.thread = threading.Thread(target=self.run_server)
        self.thread.daemon = True
        self.thread.start()
        print("Server thread spawned")
    
    def run_server(self):
        """Internal method to run the server"""
        print("Server thread starting...")
        try:
            self.server = make_server(self.host, self.port, self.app)
            print("Server is running")
            self.server.serve_forever()
        except Exception as e:
            print(f"Server error: {e}")
            self.server = None
    
    def stop(self):
        """Stop the socket server"""
        if self.server:
            print("Stopping server...")
            self.server.shutdown()
            self.server = None
            print("Server stopped")
    
    def send_vector(self, x: float, y: float):
        """
        Send vector data to all clients
        
        Args:
            x: X component of the vector
            y: Y component of the vector
        """
        if self.server:
            print(f"Sending vector: ({x}, {y})")
            self.sio.emit('vector', {'x': x, 'y': y})
