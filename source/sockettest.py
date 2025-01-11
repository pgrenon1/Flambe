import socketio
import eventlet
import eventlet.wsgi
import random

# Create a new Socket.IO server instance
sio = socketio.Server()

# Create a new WSGI application
app = socketio.WSGIApp(sio)

# Initialize last_direction
last_direction = None

# Event when a client connects
@sio.event
def connect(sid, environ):
    print(f"Client {sid} connected")
    # Send a welcome message to the client when they connect
    sio.emit('welcome', {'message': 'Welcome to the server!'}, room=sid)

# Event when a client sends a message
@sio.event
def message(sid, data):
    print(f"Received from {sid}: {data}")
    # Send an acknowledgment to the client
    sio.emit('ack', {'message': 'Message received!'}, room=sid)

# Event when a client disconnects
@sio.event
def disconnect(sid):
    print(f"Client {sid} disconnected")

def send_direction(direction):
    if direction not in ["forward", "back", "left", "right"]:
        raise ValueError("Direction must be one of: forward, back, left, right")
    print(f"Debug: Sending direction: {direction}")
    sio.emit('direction', {'direction': direction})

def send_active_state(is_active):
    print(f"Debug: Sending active state: {1 if is_active else 0}")
    sio.emit('active', {'active': 1 if is_active else 0})

# Example: sending an event to all connected clients every 5 seconds
def send_periodic_message():
    global last_direction
    while True:
        eventlet.sleep(5)
        # Get all possible directions except the last one
        possible_directions = [d for d in ["forward", "back", "left", "right", "none"] if d != last_direction]
        direction = random.choice(possible_directions)
        last_direction = direction  # Store the current direction for next time
        print(f"Debug: Emitting direction: {direction}")
        if direction != "none":
            send_active_state(True)
            send_direction(direction)
        else:
            send_active_state(False)

# Running the server using eventlet
if __name__ == '__main__':
    # Run the periodic message function in a separate green thread
    eventlet.spawn(send_periodic_message)
    print("Server is running...")
    eventlet.wsgi.server(eventlet.listen(('127.0.0.1', 12345)), app)
