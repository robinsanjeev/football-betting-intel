"""Logging setup for the Football Betting Intelligence System."""

from __future__ import annotations

import logging
import logging.handlers
import pathlib

from .config import load_config, ConfigError


def get_logger(name: str = "football_intel") -> logging.Logger:
    """Return a module-level logger configured from config.yaml.

    Falls back to a sane default (stdout, INFO) if config isn't available yet.
    """

    logger = logging.getLogger(name)
    if getattr(logger, "_configured", False):  # type: ignore[attr-defined]
        return logger

    logger.setLevel(logging.INFO)

    try:
        cfg = load_config()
        log_level = getattr(logging, cfg.logging.level.upper(), logging.INFO)
        log_file = pathlib.Path(cfg.logging.log_file)
    except ConfigError:
        log_level = logging.INFO
        log_file = pathlib.Path("football_intel/logs/system.log")

    log_file.parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5_000_000, backupCount=3
    )
    file_handler.setFormatter(fmt)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.setLevel(log_level)

    setattr(logger, "_configured", True)  # type: ignore[attr-defined]
    return logger
