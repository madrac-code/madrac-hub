"""
MADRAC MCP Server

Exposes MADRAC-SUBS capabilities as MCP tools for:
- Internal use by Ollama LLM (structured tool calling)
- External use by Claude Desktop, Cursor, or autonomous agents

Transport: stdio (Phase 3A), Streamable HTTP (Phase 3B)
"""
from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from .tools.queue import get_queue_status, pause_processing
from .tools.transcription import transcribe_file
from .tools.translation import translate_subtitles
from .tools.assistant import execute_assistant_action
from .tools.config import read_config
from .tools.dubbing import get_dubbing_status, start_dubbing

logger = logging.getLogger(__name__)

_app_state: dict[str, Any] = {}


def create_server(app_state: dict[str, Any]) -> FastMCP:
    global _app_state
    _app_state = app_state

    mcp = FastMCP(
        name="madrac-subs",
        version="3.0.0",
        description="MADRAC subtitle engine — transcription, translation, dubbing tools",
    )

    mcp.tool()(get_queue_status(_app_state))
    mcp.tool()(pause_processing(_app_state))
    mcp.tool()(transcribe_file(_app_state))
    mcp.tool()(translate_subtitles(_app_state))
    mcp.tool()(execute_assistant_action(_app_state))
    mcp.tool()(read_config(_app_state))
    mcp.tool()(get_dubbing_status(_app_state))
    mcp.tool()(start_dubbing(_app_state))

    logger.info("MADRAC MCP server created with %d tools", 8)
    return mcp


def run_server(app_state: dict[str, Any]) -> None:
    """Entry point for running the MCP server (stdio transport)."""
    server = create_server(app_state)
    server.run()
