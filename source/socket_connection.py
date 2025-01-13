import socketio
import eventlet
import eventlet.wsgi

class SocketServer:
    def __init__(self, host='127.0.0.1', port=12345):
        # Create Socket.IO server
        self.sio = socketio.Server()
        self.app = socketio.WSGIApp(self.sio)
        self.host = host
        self.port = port
        self.server = None
        
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
        eventlet.spawn(self.run_server)
    
    def run_server(self):
        """Internal method to run the server"""
        try:
            eventlet.wsgi.server(
                eventlet.listen((self.host, self.port)), 
                self.app
            )
        except Exception as e:
            print(f"Server error: {e}")
    
    def stop(self):
        """Stop the socket server"""
        if self.server:
            self.server.stop()
            print("Server stopped")
    
    def send_vector(self, x: float, y: float):
        """
        Send vector data to all clients
        
        Args:
            x: X component of the vector
            y: Y component of the vector
        """
        print(f"Sending vector: ({x}, {y})")
        self.sio.emit('vector', {'x': x, 'y': y})
