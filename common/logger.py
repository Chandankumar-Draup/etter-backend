import logging

logger = logging.getLogger("etter_app")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()

console_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
console_handler.setFormatter(console_formatter)

file_handler = logging.FileHandler("etter_logs.log")

file_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

file_handler.setFormatter(file_formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)