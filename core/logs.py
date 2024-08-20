import logging


colors = {
    "DEBUG": "\033[38;2;25;25;25m",
    "INFO": "\033[38;2;216;253;255m",
    "WARNING": "\033[38;2;255;244;68m",
    "ERROR": "\033[38;2;255;128;68m",
    "CRITICAL": "\033[38;2;255;0;0m",
    "RESET": "\033[0m",
}


class CustomFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record: logging.LogRecord):
        log_message = super().format(record)
        if record.levelname in colors:
            log_message = colors[record.levelname] + log_message + colors["RESET"]
        return log_message


logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = CustomFormatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
handler.setFormatter(formatter)
logger.addHandler(handler)

from core.config import LOGGING_LEVEL

logger.setLevel(LOGGING_LEVEL)

logger.info("Logger loaded.")
