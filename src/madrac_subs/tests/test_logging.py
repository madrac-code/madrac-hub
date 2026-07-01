"""Tests for core/logging.py."""

import logging
import os
from pathlib import Path
import pytest

from madrac.core.paths import get_user_config_dir

_TEST_LOG_DIR = get_user_config_dir() / "_test_logs"


def _make_logger(name: str) -> logging.Logger:
    """Create a clean logger with a file handler for testing."""
    _TEST_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = _TEST_LOG_DIR / f"{name}.log"

    logger = logging.getLogger(f"test_{name}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    handler = logging.FileHandler(str(log_file), encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)

    return logger


class TestLoggingManual:
    """Test logging setup directly."""

    def test_logger_writes_to_file(self):
        logger = _make_logger("write_test")
        logger.info("Test message")
        for h in logger.handlers:
            h.flush()
            h.close()
        log_file = _TEST_LOG_DIR / "write_test.log"
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "Test message" in content

    def test_unicode_logging(self):
        logger = _make_logger("unicode_test")
        logger.info("Unicode: áéíóú ñ 中文 日本語")
        for h in logger.handlers:
            h.flush()
            h.close()
        log_file = _TEST_LOG_DIR / "unicode_test.log"
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "áéíóú" in content
        assert "中文" in content

    def test_levels_written_correctly(self):
        logger = _make_logger("level_test")
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        for h in logger.handlers:
            h.flush()
            h.close()
        log_file = _TEST_LOG_DIR / "level_test.log"
        content = log_file.read_text(encoding="utf-8")
        assert "Debug message" in content
        assert "Info message" in content
        assert "Warning message" in content


class TestSetupLogging:
    """Test the actual setup_logging function."""

    def test_setup_returns_logger(self):
        from madrac.core.logging import setup_logging, get_logger
        # First call configures the root logger
        log_file = _TEST_LOG_DIR / "setup_test.log"
        logger = setup_logging(log_file=log_file)
        assert logger is not None
        assert logger.name == "madrac"
        for h in logger.handlers:
            h.flush()
            h.close()

    def test_get_logger_root(self):
        from madrac.core.logging import get_logger
        root = get_logger()
        assert root.name == "madrac"

    def test_get_logger_child(self):
        from madrac.core.logging import get_logger
        child = get_logger("child_test")
        assert child.name == "madrac.child_test"
