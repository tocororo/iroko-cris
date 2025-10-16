import logging
import logging.config
import sys
from .config import app_settings  # Import your settings


def get_logging_config():
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
        },
        "handlers": {
            "console": {
                "level": "DEBUG",
                "formatter": "default",
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
        },
    }

    # Conditionally add file handler in non-production or when explicitly enabled
    if app_settings.log_to_file:
        config["handlers"]["file"] = {
            "level": "DEBUG",
            "formatter": "detailed",
            "class": "logging.FileHandler",
            "filename": app_settings.log_file_path,
            "mode": "a",
        }
        config["loggers"]["iroko-cris"]["handlers"] = ["console", "file"]

    return config



def setup_logging():
    logging.config.dictConfig(get_logging_config())