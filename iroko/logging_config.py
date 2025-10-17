import logging
import logging.config
import sys
import os
from .config import app_settings

def get_logging_config():
    # Determine if we're in a container
    is_container = os.path.exists('/.dockerenv') or os.environ.get('CONTAINER_ENV') == 'true'
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "fmt": "%(asctime)s %(name)s %(levelname)s %(message)s %(module)s %(funcName)s",
            }
        },
        "handlers": {
            "console": {
                "level": "DEBUG",
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
            },
            "console_json": {
                "level": "DEBUG",
                "formatter": "json",
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            "iroko-cris": {
                "handlers": ["console"],
                "level": "DEBUG",
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "neo4j": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "sqlalchemy": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
        },
    }

    # In containers, never log to files and use JSON format in production
    if is_container:
        if app_settings.app_env == "production":
            # Use JSON format in production containers
            config["loggers"]["iroko-cris"]["handlers"] = ["console_json"]
            config["loggers"]["uvicorn"]["handlers"] = ["console_json"]
            config["loggers"]["uvicorn.error"]["handlers"] = ["console_json"]
            config["loggers"]["uvicorn.access"]["handlers"] = ["console_json"]
    else:
        # Only enable file logging in non-container environments when explicitly enabled
        if app_settings.log_to_file and not is_container:
            config["handlers"]["file"] = {
                "level": "DEBUG",
                "formatter": "detailed",
                "class": "logging.FileHandler",
                "filename": app_settings.log_file_path,
                "mode": "a",
            }
            config["loggers"]["iroko-cris"]["handlers"].append("file")

    return config

def setup_logging():
    logging.config.dictConfig(get_logging_config())