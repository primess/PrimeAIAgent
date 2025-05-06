import os
import logging.config # Import dictConfig
import logging.handlers # Required for RotatingFileHandler

# Create logs directory if it doesn't exist
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "app.log")

# Uvicorn logging configuration dictionary
LOGGING_CONFIG_DICT = { # Renamed to avoid conflict if we import LOGGING_CONFIG elsewhere
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(asctime)s %(levelname)s ▶ %(message)s",
            "use_colors": None,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(asctime)s %(levelname)s ▶ %(client_addr)s - "%(request_line)s" %(status_code)s',
        },
    },
    "handlers": {
        "default": { # Console handler for Uvicorn's default/error logs
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            "level": "INFO",
        },
        "access_console": { # Console handler for Uvicorn's access logs
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "level": "INFO",
        },
        "file_app": { # File handler for all application logs (root logger)
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_FILE,
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 3,
            "encoding": "utf8",
            "level": "INFO",
        },
    },
    "loggers": {
        "": { # Root logger configuration
            "handlers": ["default", "file_app"], # Log to console and file
            "level": "INFO",
            "propagate": False # Prevent root logger messages from being handled by parent (none in this case, but good practice)
        },
        "uvicorn.error": { # Uvicorn's own error logs
            "handlers": ["default", "file_app"], # Also send Uvicorn errors to our file
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": { # Uvicorn's access logs
            "handlers": ["access_console", "file_app"], # Send access logs to its console handler and our file
            "level": "INFO",
            "propagate": False,
        },
    },
}

def setup_logging():
    """Applies the logging configuration."""
    logging.config.dictConfig(LOGGING_CONFIG_DICT)