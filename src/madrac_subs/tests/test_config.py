"""Tests for the config subsystem."""

import json
import tempfile
from pathlib import Path
import pytest

from madrac.config.defaults import DEFAULTS, CONFIG_VERSION
from madrac.config.schema import (
    validate_config,
    merge_with_defaults,
    migrate_v2_to_v3,
)
from madrac.config.manager import ConfigManager


@pytest.fixture
def isolated_config(monkeypatch, tmp_path):
    """Redirect user config to a temp dir to avoid pollution from real config."""
    user_cfg = tmp_path / ".cache" / "madrac-subs"
    user_cfg.mkdir(parents=True)
    monkeypatch.setattr(
        "madrac.config.manager.get_user_config_dir",
        lambda: user_cfg,
    )
    yield user_cfg


class TestDefaults:
    def test_defaults_have_version(self):
        assert DEFAULTS["version"] == CONFIG_VERSION

    def test_defaults_have_required_sections(self):
        sections = [
            "whisper", "traduccion", "motores_traduccion",
            "subtitulos", "gui", "procesamiento", "directorios",
            "gpu", "comunidad", "plugins", "idioma",
        ]
        for s in sections:
            assert s in DEFAULTS, f"Missing section: {s}"

    def test_defaults_whisper_keys(self):
        whisper = DEFAULTS["whisper"]
        assert "modelo" in whisper
        assert "thread_count" in whisper
        assert "compute_type" in whisper


class TestValidation:
    def test_valid_defaults(self):
        warnings = validate_config(DEFAULTS)
        assert len(warnings) == 0, f"Warnings: {warnings}"

    def test_unknown_values_warn(self):
        bad = dict(DEFAULTS)
        bad["whisper"]["dispositivo"] = "quantum"
        warnings = validate_config(bad)
        assert any("dispositivo" in w for w in warnings)

    def test_wrong_type_warns(self):
        bad = dict(DEFAULTS)
        bad["whisper"]["beam_size"] = "notanint"
        warnings = validate_config(bad)
        assert any("beam_size" in w for w in warnings)


class TestMerge:
    def test_merge_empty(self):
        merged = merge_with_defaults({})
        assert merged["version"] == CONFIG_VERSION
        assert merged["whisper"]["modelo"] == "base"

    def test_merge_overrides(self):
        merged = merge_with_defaults({"whisper": {"modelo": "medium"}})
        assert merged["whisper"]["modelo"] == "medium"
        assert merged["whisper"]["compute_type"] == "int8"

    def test_merge_preserves_nested(self):
        merged = merge_with_defaults({"subtitulos": {"max_chars_por_linea": 50}})
        assert merged["subtitulos"]["max_chars_por_linea"] == 50
        assert merged["subtitulos"]["max_lineas_por_subtitulo"] == 2


class TestMigration:
    def test_migrate_v2_to_v3(self):
        v2_cfg = {
            "whisper": {"modelo": "small", "dispositivo": "cpu", "beam_size": 3},
            "traduccion": {"habilitada": True, "idioma_destino": "fr"},
            "subtitulos": {"max_chars_por_linea": 38},
        }
        v3 = migrate_v2_to_v3(v2_cfg)
        assert v3["version"] == CONFIG_VERSION
        assert v3["whisper"]["modelo"] == "small"
        assert v3["whisper"]["beam_size"] == 3
        assert v3["whisper"]["compute_type"] == "int8"
        assert v3["traduccion"]["idioma_destino"] == "fr"
        assert v3["subtitulos"]["max_chars_por_linea"] == 38


class TestConfigManager:
    def test_load_get_default_keys(self, isolated_config):
        mgr = ConfigManager()
        mgr.load()
        assert mgr.get("version") == CONFIG_VERSION
        assert mgr.get("whisper.dispositivo") == "cpu"
        assert mgr.get("nonexistent", "fallback") == "fallback"
        modelo = mgr.get("whisper.modelo")
        assert modelo in ("base", "medium", "small", "tiny")

    def test_set_and_get(self, isolated_config):
        mgr = ConfigManager()
        mgr.load()
        mgr.set("whisper.modelo", "tiny")
        assert mgr.get("whisper.modelo") == "tiny"
        assert mgr.get("whisper.dispositivo") == "cpu"

    def test_set_nested_creates_path(self, isolated_config):
        mgr = ConfigManager()
        mgr.load()
        mgr.set("custom.section.value", 42)
        assert mgr.get("custom.section.value") == 42
