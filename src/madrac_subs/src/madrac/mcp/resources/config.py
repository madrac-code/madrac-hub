"""Config MCP resources — real ConfigManager integration.

Resources:
    config://actual  — full current configuration
"""
from __future__ import annotations
import json
from typing import Any


def get_config_actual_resource(app_state: dict[str, Any]):
    async def _handler() -> str:
        """config://actual — full configuration dict."""
        cfg = app_state.get("config_manager")
        if cfg is None:
            return json.dumps({"error": "config_manager not available"}, ensure_ascii=False)
        try:
            return json.dumps(cfg.get_all(), ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    return _handler
