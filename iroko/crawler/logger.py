import logging
from logging.handlers import RotatingFileHandler
import sys

# Custom formatter con colores
class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',    
        'INFO': '\033[92m',     
        'WARNING': '\033[93m',  
        'ERROR': '\033[91m',    
        'CRITICAL': '\033[91m'  
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        message = super().format(record)
        return f"{color}{message}{self.RESET}" if color else message

def setup_logger(name='iroko-cris', log_file='app.log'):
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)


    console_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColorFormatter(console_format))

    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024, 
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(file_format))

    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

