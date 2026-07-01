"""
Logging configuration for MADRAC-SUBS v3.
Robust logging that works in dev, frozen, and windowed (no console) modes.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

from .paths import get_log_path, is_frozen


_DEFAULT_FORMAT = "[%(asctime)s] %(levelname)-7s %(name)s: %(message)s"
_DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"
_MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 3


def _get_console_stream() -> Optional[object]:
    """
    Get a safe console stream for logging.
    
    In windowed frozen mode (PyInstaller --noconsole), sys.stdout/stderr are None.
    We return os.devnull to avoid crashes.
    """
    if is_frozen() and (sys.stdout is None or sys.stderr is None):
        try:
            return open(os.devnull, "w", encoding="utf-8", errors="replace")
        except Exception:
            return None
    return sys.stderr


def setup_logging(
    level: int = logging.DEBUG,
    log_file: Optional[Path] = None,
    console_level: int = logging.INFO,
    max_bytes: int = _MAX_LOG_SIZE,
    backup_count: int = _BACKUP_COUNT,
) -> logging.Logger:
    """
    Configure application logging.
    
    Idempotent - safe to call multiple times.
    
    Args:
        level: Root logger level
        log_file: Path to log file (defaults to get_log_path())
        console_level: Console handler level
        max_bytes: Max size per log file before rotation
        backup_count: Number of rotated files to keep
        
    Returns:
        The configured root logger
    """
    logger = logging.getLogger("madrac")
    
    # Already configured?
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    logger.propagate = False
    
    formatter = logging.Formatter(_DEFAULT_FORMAT, datefmt=_DEFAULT_DATEFMT)
    
    # File handler with rotation (always enabled)
    if log_file is None:
        log_file = get_log_path()
    
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler (safe for windowed mode)
    console_stream = _get_console_stream()
    if console_stream is not None:
        console_handler = logging.StreamHandler(console_stream)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    logger.info("Logging initialized - file: %s", log_file)
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (will be prefixed with 'madrac.')
        
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"madrac.{name}")
    return logging.getLogger("madrac")


def set_qt_message_handler() -> None:
    """Install Qt message handler to redirect Qt logs to our logger."""
    try:
        from PySide6.QtCore import qInstallMessageHandler, QtMsgType
        
        qt_logger = get_logger("qt")
        _level_map = {
            QtMsgType.QtDebugMsg: logging.DEBUG,
            QtMsgType.QtInfoMsg: logging.INFO,
            QtMsgType.QtWarningMsg: logging.WARNING,
            QtMsgType.QtCriticalMsg: logging.CRITICAL,
            QtMsgType.QtFatalMsg: logging.CRITICAL,
        }
        
        def _handler(mode, context, message):
            level = _level_map.get(mode, logging.INFO)
            file = context.file or "?"
            line = context.line or 0
            qt_logger.log(level, "%s (file: %s, line: %d)", message, file, line)
        
        qInstallMessageHandler(_handler)
    except Exception:
        # Qt not available or handler failed - ignore
        pass


def log_startup_info() -> None:
    """Log useful startup information for debugging."""
    logger = get_logger("startup")
    logger.info("=== MADRAC-SUBS v3 Starting ===")
    logger.info("Python: %s", sys.version.split()[0])
    logger.info("Platform: %s", sys.platform)
    logger.info("Frozen: %s", is_frozen())
    if is_frozen():
        logger.info("Executable: %s", sys.executable)
        if hasattr(sys, "_MEIPASS"):
            logger.info("MEIPASS: %s", sys._MEIPASS)
    logger.info("Log file: %s", get_log_path())