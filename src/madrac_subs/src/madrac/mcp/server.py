"""
MADRAC MCP Server

Exposes MADRAC-SUBS capabilities as MCP tools for:
- Internal use by Ollama LLM (structured tool calling)
- External use by Claude Desktop, Cursor, or autonomous agents

Transport: stdio (Phase 3A), Streamable HTTP (Phase 3C)
"""
from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from .tools.queue import get_queue_status, pause_processing, resume_processing
from .tools.transcription import transcribe_file
from .tools.translation import translate_subtitles
from .tools.assistant import execute_assistant_action
from .tools.config import read_config
from .tools.dubbing import get_dubbing_status, start_dubbing

logger = logging.getLogger(__name__)

_app_state: dict[str, Any] = {}


def create_server(app_state: dict[str, Any]) -> FastMCP:
    """Create a FastMCP server with all MADRAC tools registered.

    Expected app_state keys:
        queue_manager    — QueueManager instance
        worker           — PipelineWorker instance (for pause/resume)
        config_manager   — ConfigManager instance
        dubbing_manager  — DubbingManager instance (optional)
        assistant_manager — AssistantManager instance (optional)
    """
    global _app_state
    _app_state = app_state

    mcp = FastMCP(
        name="madrac-subs",
        instructions="MADRAC subtitle engine — transcription, translation, dubbing tools",
    )

    mcp.tool(name="get_queue_status")(get_queue_status(_app_state))
    mcp.tool(name="pause_processing")(pause_processing(_app_state))
    mcp.tool(name="resume_processing")(resume_processing(_app_state))
    mcp.tool(name="transcribe_file")(transcribe_file(_app_state))
    mcp.tool(name="translate_subtitles")(translate_subtitles(_app_state))
    mcp.tool(name="execute_assistant_action")(execute_assistant_action(_app_state))
    mcp.tool(name="read_config")(read_config(_app_state))
    mcp.tool(name="get_dubbing_status")(get_dubbing_status(_app_state))
    mcp.tool(name="start_dubbing")(start_dubbing(_app_state))

    logger.info("MADRAC MCP server created with %d tools", 9)
    return mcp


def run_server(app_state: dict[str, Any]) -> None:
    """Entry point for running the MCP server (stdio transport). Blocking call."""
    server = create_server(app_state)
    server.run()
