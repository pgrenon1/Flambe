import logging
import os
import sys

def setup_module_logger(module_name):
    """Setup logging configuration for a module"""
    # Get the executable's directory or current directory
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    log_file = os.path.join(app_dir, 'flambe.log')
    
    # Create logger
    logger = logging.getLogger(module_name)
    
    # Only add handlers if they haven't been added yet
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Create formatters
        formatter = logging.Formatter('[%(levelname)s] - %(asctime)s - %(name)s - %(message)s')
        
        # Create handlers
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger 