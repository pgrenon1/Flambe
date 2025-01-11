import tkinter as tk
from tkinter import ttk
import subprocess
import sys
import os

def start_recording():
    record_script_path = 'record.py'
    camera_index = camera_index_entry.get()
    
    # Disable both buttons before starting process
    record_button.config(state='disabled')
    train_button.config(state='disabled')
    
    try:
        subprocess.run([sys.executable, record_script_path, 
                       '--camera-index', camera_index], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running record script: {e}")
    finally:
        # Re-enable both buttons after process completes
        record_button.config(state='normal')
        train_button.config(state='normal')

def start_training():
    train_script_path = 'train.py'
    # Disable both buttons before starting process
    record_button.config(state='disabled')
    train_button.config(state='disabled')
    
    try:
        subprocess.run([sys.executable, train_script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running training script: {e}")
    finally:
        # Re-enable both buttons after process completes
        record_button.config(state='normal')
        train_button.config(state='normal')

# Create the main window
root = tk.Tk()
root.title("Motion Recorder")

# Set a minimum window size
root.minsize(200, 150)  # Increased minimum height to accommodate new input

# Create and configure a frame to center the components
frame = tk.Frame(root)
frame.place(relx=0.5, rely=0.5, anchor='center')

# Add camera index input
camera_frame = tk.Frame(frame)
camera_frame.pack(pady=5)

camera_label = tk.Label(camera_frame, text="Camera Index:", font=('Arial', 10))
camera_label.pack(side=tk.LEFT, padx=5)

camera_index_entry = ttk.Entry(camera_frame, width=5)
camera_index_entry.insert(0, "0")  # Default camera index
camera_index_entry.pack(side=tk.LEFT)

# Create the Record button
record_button = tk.Button(
    frame,
    text="Record",
    command=start_recording,
    width=20,
    height=2,
    font=('Arial', 12)
)
record_button.pack(pady=5)

# Create the Train button
train_button = tk.Button(
    frame,
    text="Train Model",
    command=start_training,
    width=20,
    height=2,
    font=('Arial', 12)
)
train_button.pack(pady=5)

# Start the main event loop
root.mainloop()
