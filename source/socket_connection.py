import socketio
import eventlet
import eventlet.wsgi

class SocketServer:
    def __init__(self, host='127.0.0.1', port=12345):
        # Create Socket.IO server
        self.sio = socketio.Server(async_mode='eventlet')
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
        self.thread = eventlet.spawn(self.run_server)
        print("Server thread spawned")
    
    def run_server(self):
        """Internal method to run the server"""
        print("Server thread starting...")
        try:
            sock = eventlet.listen((self.host, self.port))
            self.server = eventlet.wsgi.server(sock, self.app, log_output=False)
            print("Server is running")
        except Exception as e:
            print(f"Server error: {e}")
            self.server = None
    
    def stop(self):
        """Stop the socket server"""
        if self.server:
            print("Stopping server...")
            if self.thread:
                self.thread.kill()
                self.thread = None
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
