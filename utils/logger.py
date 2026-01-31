import logging
import os
from config import Config

class Logger:
    def __init__(self):
        self.logger = logging.getLogger("GiveawayBot")
        self.logger.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        if not self.logger.handlers:
            self.logger.addHandler(console_handler)
    
    def info(self, message):
        self.logger.info(message)
    
    def error(self, message, exc_info=False):
        self.logger.error(message, exc_info=exc_info)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def debug(self, message):
        self.logger.debug(message)

# Global logger instance
logger = Logger()
