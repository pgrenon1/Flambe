from pythonosc import udp_client
import time

# Set up OSC client to send data to Unreal Engine
client = udp_client.SimpleUDPClient("127.0.0.1", 8000)

while True:
    # Send a value to control movement
    client.send_message("/game/move_forward", 1.0)  # Example command
    time.sleep(0.1)