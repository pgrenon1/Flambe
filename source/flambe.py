import tkinter as tk
from tkinter import ttk
from camera_utils import detect_cameras
from ip_camera_dialog import IPCameraDialog
from brightness_detector import BrightnessDetector
from socket_connection import SocketServer

class FlambeApp:
    def __init__(self, root):
        self.setup_window(root)
        self.setup_state()
        self.setup_ui()
        
        # Initialize socket server
        self.socket = None  # Initialize socket as None
    
    def setup_window(self, root):
        """Initialize the main window"""
        self.root = root
        self.root.title("Flambé Launcher")
        self.root.minsize(200, 250)
        
        # Create main frame
        self.frame = tk.Frame(root, padx=20, pady=20)
        self.frame.place(relx=0.5, rely=0.5, anchor='center')
        self.resize_window_to_content()
    
    def setup_state(self):
        """Initialize application state"""
        self.detector = None
        self.update_id = None
    
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
        button_frame = tk.Frame(self.frame)
        button_frame.pack(pady=10)
        
        # Brightness detection button
        self.brightness_button = tk.Button(
            button_frame,
            text="Start Flambé",
            command=self.toggle_brightness_detection,
            width=20,
            height=2,
            font=('Arial', 12),
            fg="green"
        )
        self.brightness_button.pack(pady=5)
        
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
        camera_selection = self.selected_camera.get()
        camera_arg = camera_selection.split(':')[0]
        
        try:
            self.detector = BrightnessDetector(camera_arg)
            self.detector.start()
            self.update_detector()
        except Exception as e:
            print(f"Error starting brightness detection: {e}")
            self.stop_brightness_detection()
    
    def stop_brightness_detection(self):
        """Stop brightness detection"""
        if self.detector:
            self.detector.stop()
            self.detector = None
        if self.update_id:
            self.root.after_cancel(self.update_id)
            self.update_id = None
    
    def update_detector(self):
        """Update the detector in the main GUI thread"""
        # Check if detector exists and is running
        if not self.detector or not self.detector.is_running:
            self.stop_brightness_detection()
            self.brightness_button.config(text="Start Flambé", fg="green")
            return
            
        # Try to update detector, stop if update fails
        if not self.detector.update():
            self.stop_brightness_detection()
            self.brightness_button.config(text="Start Flambé", fg="green")
            return
            
        # Get and send the current vector if server exists
        if self.socket and self.socket.server:
            vector = self.detector.get_vector()
            self.socket.send_vector(vector[0], vector[1])
            
        self.update_id = self.root.after(10, self.update_detector)
    
    def toggle_brightness_detection(self):
        """Toggle brightness detection on/off"""
        if self.detector:
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
        if self.socket:
            self.socket.stop()
        self.root.destroy()
    
    def toggle_server(self):
        """Toggle socket server on/off"""
        if self.socket and self.socket.server:
            self.socket.stop()
            self.socket = None
            self.server_button.config(text="Start Server", fg="green")
        else:
            self.socket = SocketServer()
            self.socket.start()
            self.server_button.config(text="Stop Server", fg="red")

def main():
    root = tk.Tk()
    app = FlambeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.cleanup)
    root.mainloop()

if __name__ == "__main__":
    main()
