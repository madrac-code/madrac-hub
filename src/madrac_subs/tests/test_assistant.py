"""Tests for assistant integration — lifecycle, config, and config dialog."""

import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtCore import QTimer

from madrac.assistant.manager import AssistantManager
from madrac.assistant.config import load_config, save_config
from madrac.ui.dialogs.assistant_config_dialog import AssistantConfigDialog


@pytest.fixture(autouse=True)
def isolated_config(tmp_path):
    """Redirect assistant config to a temp dir for test isolation."""
    import madrac.assistant.config as cfg_mod
    original_writable = cfg_mod._assistant_root
    def _fake_root():
        return tmp_path
    cfg_mod._assistant_root = _fake_root
    yield
    cfg_mod._assistant_root = original_writable


class TestAssistantManager:
    def test_initial_state(self):
        mgr = AssistantManager()
        assert not mgr.is_running

    def test_start_stop_does_not_crash(self, qtbot):
        mgr = AssistantManager()
        with patch.object(mgr, "_run"):
            mgr.start()
            assert mgr._thread is not None
            mgr.stop()

    def test_stop_without_start(self):
        mgr = AssistantManager()
        mgr.stop()

    def test_double_start_safe(self, qtbot):
        mgr = AssistantManager()
        with patch.object(mgr, "_run"):
            mgr.start()
            mgr.start()
            mgr.stop()

    def test_start_emits_error_on_missing_base(self, qtbot):
        mgr = AssistantManager()
        errors = []
        mgr.error_occurred.connect(lambda m: errors.append(m))
        with patch("madrac.assistant.manager._ensure_importable") as mock:
            mock.side_effect = RuntimeError("not found")
            mgr.start()
            assert len(errors) == 1

    def test_state_changed_signals(self, qtbot):
        mgr = AssistantManager()
        states = []
        mgr.state_changed.connect(lambda v: states.append(v))

        def mock_run():
            mgr._running = True
            mgr.state_changed.emit(True)

        with patch.object(mgr, "_run", side_effect=mock_run):
            mgr.start()
            mgr._thread.join(timeout=5)
            qtbot.wait(50)
            assert len(states) >= 1

    def test_full_lifecycle_signals(self, qtbot):
        mgr = AssistantManager()
        states = []
        mgr.state_changed.connect(lambda v: states.append(v))

        def mock_run():
            mgr._running = True
            mgr.state_changed.emit(True)

        with patch.object(mgr, "_run", side_effect=mock_run):
            mgr.start()
            mgr._thread.join(timeout=5)
            mgr.stop()
            qtbot.wait(50)
            assert True in states
            assert False in states


class TestAssistantConfig:
    def test_load_config_returns_dict(self):
        cfg = load_config()
        assert isinstance(cfg, dict)

    def test_save_and_load_roundtrip(self):
        original = {"test_key": "test_value", "number": 42}
        save_config(original)
        loaded = load_config()
        assert loaded.get("test_key") == "test_value"
        assert loaded.get("number") == 42

    def test_load_config_with_settings(self):
        cfg = load_config()
        if cfg:
            assert "modelo_ia" in cfg or "whisper" in cfg


class TestAssistantConfigDialog:
    def test_dialog_creation(self, qtbot):
        dialog = AssistantConfigDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() != ""

    def test_dialog_not_modal(self):
        dialog = AssistantConfigDialog()
        assert not dialog.isModal()

    def test_dialog_loads_existing_config(self, qtbot):
        cfg = load_config()
        dialog = AssistantConfigDialog()
        qtbot.addWidget(dialog)
        if cfg:
            model = dialog._ollama_model.text()
            assert isinstance(model, str)
