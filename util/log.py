import sys
from loguru import logger

config = {
    "handlers": [
        {"sink": sys.stdout,
         "format": "<d>{time:HH:mm:ss}</d> <level>{level: >8} |</level> {message}"},
    ],
}

logger.configure(**config)
