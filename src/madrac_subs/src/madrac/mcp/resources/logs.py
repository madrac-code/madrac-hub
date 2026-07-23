"""Log MCP resources — ring-buffer log capture.

Resources:
    log://ultimos/{n}  — last n log entries from the ring buffer

The log_buffer is populated automatically when the MCP server is
started via AssistantManager.start_mcp_server() — it installs a
logging.Handler on the madrac root logger.
"""
from __future__ import annotations
import json
from typing import Any


def get_ultimos_logs_resource(app_state: dict[str, Any]):
    async def _handler(n: int) -> str:
        """log://ultimos/{n} — last n log entries from ring buffer."""
        buf = app_state.get("log_buffer")
        if buf is None:
            return json.dumps({
                "error": "log_buffer not in app_state",
                "note": "add log_buffer to AssistantManager.start_mcp_server()",
            }, ensure_ascii=False)
        try:
            entries = list(buf)[-n:] if n > 0 else []
            return json.dumps(entries, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    return _handler
