"""Simple logging wrapper for ai_finance_assistant."""

import logging
import sys


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Return a configured logger with the given name.

    Logging format:  [LEVEL]  logger_name — message

    Parameters
    ----------
    name : str
        Typically __name__ of the calling module.
    level : int
        Logging level (default: logging.INFO).

    Returns
    -------
    logging.Logger
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

    logger.setLevel(level)
    return logger
