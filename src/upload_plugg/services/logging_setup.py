from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from ..paths import AppPaths


def configure_logging(paths: AppPaths) -> logging.Logger:
    logger = logging.getLogger("upload_plugg")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(threadName)s %(message)s"
    )
    handler = RotatingFileHandler(
        paths.logs / "upload_plugg.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger

