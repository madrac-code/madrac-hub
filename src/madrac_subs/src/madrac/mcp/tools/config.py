"""Config read MCP tools — real ConfigManager integration."""
from __future__ import annotations
from typing import Any


def read_config(app_state: dict[str, Any]):
    async def _read_config(clave: str = "") -> dict:
        """
        Read the current MADRAC configuration via ConfigManager.

        Args:
            clave: Optional dot-notation key (e.g. 'whisper.modelo').
                   If empty, returns the full config dict.

        Returns:
            Config value or full config dict.
        """
        config_mgr = app_state.get("config_manager")
        if config_mgr is None:
            return {"error": "config_manager not available"}
        try:
            if not clave:
                return config_mgr.get_all()
            value = config_mgr.get(clave)
            return {"value": value}
        except Exception as e:
            return {"error": str(e)}
    return _read_config
