"""Config read MCP tools."""
from __future__ import annotations
from typing import Any


def read_config(app_state: dict[str, Any]):
    async def _read_config(clave: str = "") -> dict:
        """
        Read the current MADRAC configuration.

        Args:
            clave: Optional dot-notation key (e.g. 'whisper.modelo').
                   If empty, returns the full config.

        Returns:
            Config value or full config dict.
        """
        config = app_state.get("config")
        if config is None:
            return {"error": "config not available"}
        if not clave:
            return config.to_dict() if hasattr(config, "to_dict") else {}
        keys = clave.split(".")
        value = config
        for k in keys:
            value = getattr(value, k, None)
            if value is None:
                return {"error": f"Key '{clave}' not found"}
        return {"value": value}
    return _read_config
