import tkinter as tk
from tkinter import ttk

class IPCameraDialog:
    def __init__(self, parent):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Connect IP Camera")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Set icon
        self.dialog.iconbitmap('./assets/fire.ico')
        
        # Center the dialog
        window_width = 300
        window_height = 200
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Create main frame
        frame = ttk.Frame(self.dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # IP Address entry
        ttk.Label(frame, text="IP Address:").pack(anchor=tk.W)
        self.address_var = tk.StringVar(value="192.168.0.197")
        self.address_entry = ttk.Entry(frame, textvariable=self.address_var)
        self.address_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Port entry
        ttk.Label(frame, text="Port:").pack(anchor=tk.W)
        self.port_var = tk.StringVar(value="8080")
        self.port_entry = ttk.Entry(frame, textvariable=self.port_var)
        self.port_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Buttons frame
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Confirm button
        ttk.Button(
            button_frame,
            text="Confirm",
            command=self.confirm
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        # Cancel button
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel
        ).pack(side=tk.RIGHT)
        
        # Configure dialog behavior
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        self.dialog.bind("<Return>", lambda e: self.confirm())
        self.dialog.bind("<Escape>", lambda e: self.cancel())
        
        # Focus first entry
        self.address_entry.focus_set()
        
        # Wait for dialog to close
        parent.wait_window(self.dialog)
    
    def confirm(self):
        """Save the connection details and close dialog"""
        self.result = (self.address_var.get(), self.port_var.get())
        self.dialog.destroy()
    
    def cancel(self):
        """Close dialog without saving"""
        self.dialog.destroy() 