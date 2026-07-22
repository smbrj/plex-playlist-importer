from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime


def setup_logging(
    level: str = "INFO",
    directory: Path | str = Path("logs"),
    filename: str = "playlist_import.log",
) -> logging.Logger:
    """Configure console, rotating, debug, and per-run logging."""

    log_dir = Path(directory)
    run_dir = log_dir / "runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("plex_playlist")

    # setup_logging may be called more than once in tests or embedded use.
    # Existing handlers mean the logger is already configured.
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setLevel(level.upper())
    console.setFormatter(formatter)

    rotating = logging.handlers.RotatingFileHandler(
        log_dir / filename,
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    rotating.setLevel(logging.INFO)
    rotating.setFormatter(formatter)

    debug = logging.handlers.RotatingFileHandler(
        log_dir / "debug.log",
        maxBytes=20_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    debug.setLevel(logging.DEBUG)
    debug.setFormatter(formatter)

    runfile = run_dir / (datetime.now().strftime("%Y%m%d-%H%M%S") + ".log")
    run = logging.FileHandler(runfile, encoding="utf-8")
    run.setLevel(logging.DEBUG)
    run.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(rotating)
    logger.addHandler(debug)
    logger.addHandler(run)

    logger.info("Logging initialized")
    return logger

