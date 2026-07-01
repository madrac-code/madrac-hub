"""Configuration manager with TOML persistence and v2 compat."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.paths import (
    is_frozen,
    get_user_config_dir,
    get_user_config_path,
    get_config_path,
)
from ..core.logging import get_logger
from .defaults import DEFAULTS, CONFIG_VERSION
from .schema import validate_config, merge_with_defaults, migrate_v2_to_v3

logger = get_logger("config")

try:
    import tomllib
except ImportError:
    tomllib = None  # Python <3.11, will need tomli

_TOML_WARNING_SHOWN = False


def _try_load_toml(path: Path) -> Optional[Dict[str, Any]]:
    """Load a TOML file if possible. Returns None on failure."""
    global _TOML_WARNING_SHOWN
    if not path.exists():
        return None
    try:
        if tomllib:
            with open(path, "rb") as f:
                return tomllib.load(f)
        else:
            import tomli
            with open(path, "rb") as f:
                return tomli.load(f)
    except Exception as e:
        if not _TOML_WARNING_SHOWN:
            logger.warning("Failed to load TOML %s: %s", path, e)
            _TOML_WARNING_SHOWN = True
        return None


def _try_load_json(path: Path) -> Optional[Dict[str, Any]]:
    """Load a JSON file. Returns None on failure."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load JSON %s: %s", path, e)
        return None


def _try_save_toml(path: Path, data: Dict[str, Any]) -> bool:
    """Save a dict to TOML file. Falls back to JSON if TOML not available."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import tomli_w
        with open(path, "wb") as f:
            tomli_w.dump(data, f)
        logger.debug("Config saved to TOML: %s", path)
        return True
    except ImportError:
        logger.debug("tomli_w not available, saving config as JSON")
        json_path = path.with_suffix(".json")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Config saved to JSON: %s", json_path)
            return True
        except Exception as e:
            logger.error("Failed to save config: %s", e)
            return False
    except Exception as e:
        logger.error("Failed to save TOML config: %s", e)
        json_path = path.with_suffix(".json")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Config saved to JSON (fallback): %s", json_path)
            return True
        except Exception as je:
            logger.error("Failed to save config (JSON fallback): %s", je)
            return False


_USER_CONFIG_TOML = "config.toml"


def _user_toml_path() -> Path:
    return get_user_config_dir() / _USER_CONFIG_TOML


def _user_json_path() -> Path:
    return get_user_config_dir() / "config.json"


class ConfigManager:
    """Central configuration manager.

    Load order:
    1. Built-in defaults (DEFAULTS dict)
    2. Bundled config file (read-only, from package or sys._MEIPASS)
    3. User persistent config (~/.cache/madrac-subs/config.toml)
    """

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._user_path: Path = _user_toml_path()
        self._loaded = False

    def load(self) -> None:
        """Load and merge all config sources."""
        # Start with defaults
        cfg = dict(DEFAULTS)

        # Try bundled config (read-only fallback)
        bundled_path = get_config_path()
        if bundled_path and bundled_path.exists():
            if bundled_path.suffix == ".toml":
                bundled = _try_load_toml(bundled_path)
            else:
                bundled = _try_load_json(bundled_path)
            if bundled:
                cfg = merge_with_defaults(bundled)

        # Try user config (TOML first, then JSON for v2 migration)
        user_cfg = _try_load_toml(self._user_path)
        if user_cfg is None:
            json_path = _user_json_path()
            if json_path.exists():
                raw_cfg = _try_load_json(json_path)
                if raw_cfg:
                    if raw_cfg.get("version", 0) >= 3:
                        user_cfg = raw_cfg
                    else:
                        user_cfg = migrate_v2_to_v3(raw_cfg)
                    _try_save_toml(self._user_path, user_cfg)

        # Also check JSON fallback (in case TOML save failed silently)
        json_path = _user_json_path()
        toml_path = self._user_path
        if json_path.exists():
            json_mtime = json_path.stat().st_mtime
            toml_mtime = toml_path.stat().st_mtime if toml_path.exists() else 0
            if json_mtime > toml_mtime:
                json_cfg = _try_load_json(json_path)
                if json_cfg and json_cfg != user_cfg:
                    json_cfg = merge_with_defaults(json_cfg)
                    # Merge JSON keys into user_cfg (JSON wins for individual keys)
                    if user_cfg:
                        user_cfg.update(json_cfg)
                    else:
                        user_cfg = json_cfg
                    # Re-save as TOML to sync
                    if user_cfg:
                        _try_save_toml(toml_path, user_cfg)

        if user_cfg:
            cfg = merge_with_defaults(user_cfg)

        # Validate
        warnings = validate_config(cfg)
        for w in warnings:
            logger.warning("Config: %s", w)

        self._data = cfg
        self._loaded = True
        logger.debug("Config loaded (version=%d)", cfg.get("version"))

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by dotted key."""
        if not self._loaded:
            self.load()
        keys = key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
                if val is None:
                    return default
            else:
                return default
        return val if val is not None else default

    def set(self, key: str, value: Any) -> None:
        """Set a config value by dotted key and persist."""
        if not self._loaded:
            self.load()
        keys = key.split(".")
        target = self._data
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self._save()

    def _save(self) -> bool:
        """Persist config to user TOML file. Returns True on success."""
        if not self._loaded:
            return False
        self._data["version"] = CONFIG_VERSION
        return _try_save_toml(self._user_path, self._data)

    def reset_to_defaults(self) -> None:
        """Reset config to factory defaults."""
        self._data = dict(DEFAULTS)
        self._data["version"] = CONFIG_VERSION
        self._save()

    def get_all(self) -> Dict[str, Any]:
        """Return full config dict (read-only snapshot)."""
        if not self._loaded:
            self.load()
        from copy import deepcopy
        return deepcopy(self._data)

    def get_raw_ref(self) -> Dict[str, Any]:
        """Return the internal config dict (for performance-sensitive code)."""
        if not self._loaded:
            self.load()
        return self._data


# Global singleton
_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    global _manager
    if _manager is None:
        _manager = ConfigManager()
    return _manager


def get_config(key: str, default: Any = None) -> Any:
    return get_config_manager().get(key, default)


def set_config(key: str, value: Any) -> None:
    get_config_manager().set(key, value)
