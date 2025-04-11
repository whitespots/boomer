from loguru import logger

import sys


def setup_logger(verbose=False, log_file=None):
    # Remove default handler
    logger.remove()

    # Add console handler with appropriate level
    log_level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}", level=log_level, colorize=True)

    # Add file handler if specified
    if log_file:
        logger.add(log_file, rotation="10 MB", retention="1 week")

    return logger


logs = setup_logger()
