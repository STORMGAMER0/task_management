import logging
import sys
import json
from datetime import datetime
from typing import Any
from core.config import settings

class JSONFormatter(logging.Formatter):
    #this clas outputs logs in JSON format
    def format(self, record:logging.LogRecord):
        log_data = {
            "time" : datetime.now().isoformat(),
            "level" : record.levelname,
            "message" : record.getMessage(),
            "module" : record.module,
            "function": record.funcName,
            "line" : record.lineno
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        return json.dumps(log_data)

class ColoredFormatter(logging.Formatter):

    #colored formatter for console output to make log easier to read in development

    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',  # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',  # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'  # Reset
    }

    def format(self, record: logging.LogRecord):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"

        formatted = super().format(record)

        record.levelname = levelname

        return formatted

def setup_logging():
    #configures app logging
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)

    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)

    if settings.is_development:
        console_formatter = ColoredFormatter(fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S")
        console_handler.setFormatter(console_formatter)
    else:
        console_handler.setFormatter(JSONFormatter())

    root_logger.addHandler(console_handler)

    if settings.is_production:
        file_handler = logging.FileHandler("app.log")
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

        # Silence third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={settings.log_level}, environment={settings.environment}"
    )


def get_logger(name: str) -> logging.Logger:

    return logging.getLogger(name)




