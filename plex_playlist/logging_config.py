from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime


LOG_DIR = Path("logs")
RUN_DIR = LOG_DIR / "runs"


def setup_logging(
    level: str = "INFO",
) -> logging.Logger:

    LOG_DIR.mkdir(exist_ok=True)
    RUN_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger("plex_playlist")

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    #
    # Console
    #

    console = logging.StreamHandler()
    console.setLevel(level.upper())
    console.setFormatter(formatter)

    #
    # Rotating application log
    #

    rotating = logging.handlers.RotatingFileHandler(
        LOG_DIR / "importer.log",
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
    )

    rotating.setLevel(logging.INFO)
    rotating.setFormatter(formatter)

    #
    # Full debug log
    #

    debug = logging.handlers.RotatingFileHandler(
        LOG_DIR / "debug.log",
        maxBytes=20_000_000,
        backupCount=3,
        encoding="utf-8",
    )

    debug.setLevel(logging.DEBUG)
    debug.setFormatter(formatter)

    #
    # Per-run log
    #

    runfile = RUN_DIR / (
        datetime.now().strftime("%Y%m%d-%H%M%S") + ".log"
    )

    run = logging.FileHandler(
        runfile,
        encoding="utf-8",
    )

    run.setLevel(logging.DEBUG)
    run.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(rotating)
    logger.addHandler(debug)
    logger.addHandler(run)

    logger.info("Logging initialized")

    return logger