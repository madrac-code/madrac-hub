"""Tests for core/paths.py path resolution."""

import sys
from pathlib import Path
import pytest

from madrac.core.paths import (
    is_frozen,
    get_base_path,
    get_project_root,
    get_user_config_dir,
    get_log_path,
    get_queue_path,
    get_temp_dir,
    get_plugins_dir,
    get_resource_path,
)


class TestPaths:
    def test_is_frozen_false_in_dev(self):
        assert is_frozen() is False

    def test_get_base_path_is_project_root(self):
        base = get_base_path()
        assert base.exists()
        # Expect project root (contains src/, config.json, main.py)
        assert (base / "src").is_dir()

    def test_get_project_root(self):
        root = get_project_root()
        assert root.exists()
        assert (root / "src").is_dir()

    def test_get_user_config_dir(self):
        cfg_dir = get_user_config_dir()
        expected = Path.home() / ".cache" / "madrac-subs"
        assert cfg_dir == expected

    def test_get_log_path(self):
        log_path = get_log_path()
        expected = Path.home() / ".cache" / "madrac-subs" / "madrac-subs.log"
        assert log_path == expected

    def test_get_queue_path(self):
        q_path = get_queue_path()
        expected = Path.home() / ".cache" / "madrac-subs" / "queue.json"
        assert q_path == expected

    def test_get_temp_dir(self):
        temp_dir = get_temp_dir()
        assert str(temp_dir)  # Should return a path

    def test_get_plugins_dir(self):
        plugins = get_plugins_dir()
        assert plugins  # Should return a path
        assert "plugins" in str(plugins)

    def test_get_resource_path_ui_exists(self):
        # The resources/ui directory should exist (or at least resolve somewhere)
        ui_path = get_resource_path("ui")
        assert ui_path  # Returns some path
