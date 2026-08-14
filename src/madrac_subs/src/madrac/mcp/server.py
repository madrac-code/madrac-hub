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
from .tools.workspace import (
    get_workspace_info,
    list_workspaces,
    get_segments,
    rename_speaker,
    edit_subtitle_segment,
    export_srt,
)
from .tools.ui import (
    create_window,
    update_widget,
    close_window,
    list_windows,
    get_window_events,
)
from .tools.recon import diarize_speakers
from .tools.recon_map import register as register_recon_map
from .resources.queue import get_queue_estado_resource, get_queue_progreso_resource
from .resources.config import get_config_actual_resource
from .resources.logs import get_ultimos_logs_resource

logger = logging.getLogger(__name__)

_app_state: dict[str, Any] = {}


def create_server(app_state: dict[str, Any]) -> FastMCP:
    """Create a FastMCP server with all MADRAC tools and resources registered.

    Expected app_state keys:
        queue_manager     — QueueManager instance
        worker            — PipelineWorker instance (for pause/resume)
        config_manager    — ConfigManager instance
        dubbing_manager   — DubbingManager instance (optional)
        assistant_manager — AssistantManager instance (optional)
        ui_manager        — UIManager instance (optional, for MUI tools)
        log_buffer        — collections.deque ring buffer (optional)
    """
    global _app_state
    _app_state = app_state

    mcp = FastMCP(
        name="madrac-subs",
        instructions="MADRAC subtitle engine — transcription, translation, dubbing tools",
    )

    # ── Tools ─────────────────────────────────────────────────────
    mcp.tool(name="get_queue_status")(get_queue_status(_app_state))
    mcp.tool(name="pause_processing")(pause_processing(_app_state))
    mcp.tool(name="resume_processing")(resume_processing(_app_state))
    mcp.tool(name="transcribe_file")(transcribe_file(_app_state))
    mcp.tool(name="translate_subtitles")(translate_subtitles(_app_state))
    mcp.tool(name="execute_assistant_action")(execute_assistant_action(_app_state))
    mcp.tool(name="read_config")(read_config(_app_state))
    mcp.tool(name="get_dubbing_status")(get_dubbing_status(_app_state))
    mcp.tool(name="start_dubbing")(start_dubbing(_app_state))
    # Workspace tools
    mcp.tool(name="get_workspace_info")(get_workspace_info(_app_state))
    mcp.tool(name="list_workspaces")(list_workspaces(_app_state))
    mcp.tool(name="get_segments")(get_segments(_app_state))
    mcp.tool(name="rename_speaker")(rename_speaker(_app_state))
    mcp.tool(name="edit_subtitle_segment")(edit_subtitle_segment(_app_state))
    mcp.tool(name="export_srt")(export_srt(_app_state))
    # MUI window tools
    mcp.tool(name="create_window")(create_window(_app_state))
    mcp.tool(name="update_widget")(update_widget(_app_state))
    mcp.tool(name="close_window")(close_window(_app_state))
    mcp.tool(name="list_windows")(list_windows(_app_state))
    mcp.tool(name="get_window_events")(get_window_events(_app_state))
    # RECON tools
    mcp.tool(name="diarize_speakers")(diarize_speakers(_app_state))
    register_recon_map(mcp)

    # ── Resources ─────────────────────────────────────────────────
    mcp.resource(
        "queue://estado",
        name="Queue State",
        description="Full queue summary with item details",
    )(get_queue_estado_resource(_app_state))

    mcp.resource(
        "queue://progreso/{job_id}",
        name="Queue Progress",
        description="Single queue item progress by job ID",
    )(get_queue_progreso_resource(_app_state))

    mcp.resource(
        "config://actual",
        name="Current Config",
        description="Full MADRAC configuration",
    )(get_config_actual_resource(_app_state))

    mcp.resource(
        "log://ultimos/{n}",
        name="Recent Logs",
        description="Last N log entries from ring buffer",
    )(get_ultimos_logs_resource(_app_state))

    logger.info("MADRAC MCP server created (22 tools, 4 resources)")
    return mcp


def run_server(app_state: dict[str, Any]) -> None:
    """Entry point for running the MCP server (stdio transport). Blocking call."""
    server = create_server(app_state)
    server.run()
