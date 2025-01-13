import tkinter as tk
from tkinter import ttk
import subprocess
import sys
import os
import signal
from camera_utils import detect_cameras
from ip_camera_dialog import IPCameraDialog

class FlambeApp:
    def __init__(self, root):
        self.setup_window(root)
        self.setup_state()
        self.setup_ui()
        
    def setup_window(self, root):
        """Initialize the main window"""
        self.root = root
        self.root.title("Flambé Launcher")
        self.root.minsize(200, 250)
        
        # Create main frame
        self.frame = tk.Frame(root, padx=20, pady=20)
        self.frame.place(relx=0.5, rely=0.5, anchor='center')
    
    def setup_state(self):
        """Initialize application state"""
        self.current_process = None
        self.brightness_running = False
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setup_camera_selection()
        self.setup_buttons()
        self.resize_window_to_content()
    
    def setup_camera_selection(self):
        """Setup camera selection UI"""
        # Show loading message
        loading_label = tk.Label(self.frame, text="Detecting Cameras...", font=('Arial', 12))
        loading_label.pack(pady=20)
        self.root.update()
        
        # Detect cameras
        self.cameras = detect_cameras()
        loading_label.destroy()
        
        # Create camera selection frame
        camera_frame = tk.LabelFrame(self.frame, text="Select Camera", padx=10, pady=5)
        camera_frame.pack(pady=10, fill="x")
        
        # Setup camera options
        self.camera_options = [(idx, name) for idx, name in self.cameras]
        self.camera_options.append(('ip', 'Connect IP Camera...'))
        
        # Create camera selection dropdown
        self.selected_camera = ttk.Combobox(
            camera_frame,
            values=[f"{idx}: {name}" for idx, name in self.camera_options],
            state="readonly",
            width=30
        )
        self.selected_camera.pack(pady=10)
        
        # Set default camera
        default_camera = f"{self.cameras[0][0]}: {self.cameras[0][1]}" if self.cameras else "0: Default Camera"
        self.selected_camera.set(default_camera)
        
        # Bind camera selection change
        self.selected_camera.bind('<<ComboboxSelected>>', self.on_camera_change)
    
    def setup_buttons(self):
        """Setup control buttons"""
        # Brightness detection button
        self.brightness_button = tk.Button(
            self.frame,
            text="Start Flambé",
            command=self.toggle_brightness_detection,
            width=20,
            height=2,
            font=('Arial', 12),
            fg="green"
        )
        self.brightness_button.pack(pady=(5, 20))
    
    def start_brightness_detection(self):
        """Start brightness detection process"""
        camera_selection = self.selected_camera.get()
        camera_arg = camera_selection.split(':')[0]
        
        try:
            self.current_process = subprocess.Popen(
                [sys.executable, 'source/brightness_detector.py', 
                 '--camera-index', camera_arg],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            self.brightness_running = True
            
        except subprocess.CalledProcessError as e:
            print(f"Error running brightness detection: {e}")
    
    def stop_brightness_detection(self):
        """Stop brightness detection process"""
        self.brightness_running = False
        if self.current_process:
            if os.name == 'nt':
                self.current_process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                self.current_process.terminate()
            self.current_process.wait()
            self.current_process = None
    
    def toggle_brightness_detection(self):
        """Toggle brightness detection on/off"""
        if self.brightness_running:
            self.stop_brightness_detection()
            self.brightness_button.config(text="Start Flambé", fg="green")
        else:
            self.start_brightness_detection()
            self.brightness_button.config(text="Stop Flambé", fg="red")
    
    def on_camera_change(self, event):
        """Handle camera selection change"""
        if self.selected_camera.get().startswith("ip:"):
            self.show_ip_camera_dialog()
    
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

def main():
    root = tk.Tk()
    app = FlambeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.cleanup)
    root.mainloop()

if __name__ == "__main__":
    main()
