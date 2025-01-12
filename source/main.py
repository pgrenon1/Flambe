import tkinter as tk
from tkinter import ttk
import subprocess
import sys
import os
import signal
from camera_utils import detect_cameras

class BrightnessDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Flambé")
        self.root.minsize(200, 250)
        
        self.current_process = None
        
        # Create and configure a frame to center the components
        self.frame = tk.Frame(root, padx=20, pady=20)
        self.frame.place(relx=0.5, rely=0.5, anchor='center')
        
        # Create loading label
        loading_label = tk.Label(self.frame, text="Detecting Cameras...", font=('Arial', 12))
        loading_label.pack(pady=20)
        self.root.update()  # Force update to show loading message
        
        # Setup camera selection
        self.cameras = detect_cameras()
        
        # Remove loading label
        loading_label.destroy()
        
        # Camera selection frame
        self.camera_frame = tk.LabelFrame(self.frame, text="Select Camera", padx=10, pady=5)
        self.camera_frame.pack(pady=10, fill="x")
        
        # Add IP Camera option to the list
        self.camera_options = [(idx, name) for idx, name in self.cameras]
        self.camera_options.append(('ip', 'Connect IP Camera...'))
        
        # Create combobox for camera selection
        self.selected_camera = ttk.Combobox(
            self.camera_frame,
            values=[f"{idx}: {name}" for idx, name in self.camera_options],
            state="readonly",
            width=30
        )
        self.selected_camera.pack(pady=10)
        
        # Set default camera
        if self.cameras:
            self.selected_camera.set(f"{self.cameras[0][0]}: {self.cameras[0][1]}")
        else:
            self.selected_camera.set("0: Default Camera")
        
        # Bind camera selection change
        self.selected_camera.bind('<<ComboboxSelected>>', self.on_camera_change)
        
        # Create the Brightness button
        self.brightness_button = tk.Button(
            self.frame,
            text="Live Brightness Detection",
            command=self.toggle_brightness_detection,
            width=20,
            height=2,
            font=('Arial', 12)
        )
        self.brightness_button.pack(pady=(5, 20))
        
        # Resize main window to fit content
        self.resize_window_to_content(self.root, self.frame)
        
        # Flag to track if brightness detection is running
        self.brightness_running = False
    
    def on_camera_change(self, event=None):
        """Handle camera selection change"""
        selection = self.selected_camera.get()
        camera_id = selection.split(':')[0].strip()
        
        if camera_id == 'ip':
            # Show IP camera dialog
            result = self.show_ip_camera_dialog()
            if result:
                ip, port = result
                # Add the IP camera to the list if not already present
                camera_text = f"ip:{ip}:{port}"
                if camera_text not in self.selected_camera['values']:
                    values = list(self.selected_camera['values'])
                    values.insert(-1, camera_text)  # Insert before the "Connect IP Camera..." option
                    self.selected_camera['values'] = values
                self.selected_camera.set(camera_text)
            else:
                # If dialog was cancelled, revert to previous selection
                self.selected_camera.set(self.selected_camera.get())
        
        if self.brightness_running:
            self.restart_brightness_detection()
    
    def show_ip_camera_dialog(self):
        """Show dialog to input IP camera details"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Connect IP Camera")
        
        # Create main frame for dialog
        dialog_frame = tk.Frame(dialog, padx=20, pady=20)
        dialog_frame.pack(expand=True, fill='both')
        
        tk.Label(dialog_frame, text="IP Address:").pack(pady=5)
        ip_entry = tk.Entry(dialog_frame)
        ip_entry.pack(pady=5)
        ip_entry.insert(0, "192.168.1.")
        
        tk.Label(dialog_frame, text="Port:").pack(pady=5)
        port_entry = tk.Entry(dialog_frame)
        port_entry.pack(pady=5)
        port_entry.insert(0, "8080")
        
        def on_connect():
            dialog.result = (ip_entry.get(), port_entry.get())
            dialog.destroy()
        
        def on_cancel():
            dialog.result = None
            dialog.destroy()
        
        button_frame = tk.Frame(dialog_frame)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Connect", command=on_connect).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
        # Resize dialog to fit content
        self.resize_window_to_content(dialog, dialog_frame, padding_x=20, padding_y=20)
        
        # Position dialog to the right of main window
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        dialog_x = main_x + main_width + 10
        dialog_y = main_y
        dialog.geometry(f"+{dialog_x}+{dialog_y}")
        
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.wait_window()
        
        return getattr(dialog, 'result', None)
    
    def toggle_brightness_detection(self):
        """Toggle brightness detection on/off"""
        if self.brightness_running:
            self.stop_brightness_detection()
            self.brightness_button.config(text="Live Brightness Detection")
        else:
            self.start_brightness_detection()
            self.brightness_button.config(text="Stop Brightness Detection")
    
    def start_brightness_detection(self):
        """Start brightness detection process"""
        camera_selection = self.selected_camera.get()
        # Handle IP camera format "ip:address:port" differently from regular camera index
        if camera_selection.startswith('ip:'):
            camera_arg = camera_selection  # Pass the full ip:address:port string
        else:
            camera_arg = camera_selection.split(':')[0]  # Just get the camera index
        
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
        if self.current_process:
            if os.name == 'nt':
                self.current_process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                self.current_process.terminate()
            self.current_process.wait()
            self.current_process = None
        self.brightness_running = False
    
    def restart_brightness_detection(self):
        """Restart brightness detection with new camera"""
        if self.brightness_running:
            self.stop_brightness_detection()
            self.start_brightness_detection()
    
    def resize_window_to_content(self, window, frame, padding_x=40, padding_y=40):
        """
        Resize a window to fit its content with padding
        
        Args:
            window: The window to resize
            frame: The frame containing the content
            padding_x: Horizontal padding (default 40)
            padding_y: Vertical padding (default 40)
        """
        window.update()
        frame_width = frame.winfo_reqwidth()
        frame_height = frame.winfo_reqheight()
        window_width = frame_width + padding_x
        window_height = frame_height + padding_y
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        window.geometry(f"{window_width}x{window_height}+{x}+{y}")

if __name__ == "__main__":
    root = tk.Tk()
    root.iconbitmap("./fire.ico")
    app = BrightnessDetectorApp(root)
    root.mainloop()
