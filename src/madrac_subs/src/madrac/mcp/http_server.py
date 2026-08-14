"""
MADRAC MCP HTTP Server — Streamable HTTP transport.

Listens on 127.0.0.1:7654 (localhost only).
Auth: Bearer token from ~/.cache/madrac-subs/mcp_token.txt

External agents connect via:
  POST http://127.0.0.1:7654/mcp
  Authorization: Bearer <token>
  Content-Type: application/json
  Body: {"jsonrpc": "2.0", "method": "...", "params": {...}, "id": 1}
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from aiohttp import web

from .auth import get_or_create_token, validate_token, get_token_path
from .server import create_server

logger = logging.getLogger(__name__)

HOST = "127.0.0.1"
PORT = int(os.environ.get("MADRAC_MCP_PORT", "7654"))


class MCPHttpServer:
    """
    Wraps the FastMCP server with an aiohttp HTTP layer.
    Handles auth and JSON-RPC routing.
    """

    def __init__(self, app_state: dict[str, Any]) -> None:
        self.app_state = app_state
        self.mcp_server = create_server(app_state)
        self.token = get_or_create_token()
        self._runner: web.AppRunner | None = None

    async def start(self) -> None:
        """Start the HTTP server."""
        app = web.Application(middlewares=[self._auth_middleware])
        app.router.add_post("/mcp", self._handle_mcp)
        app.router.add_get("/health", self._handle_health)
        app.router.add_get("/tools", self._handle_list_tools)

        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, HOST, PORT)
        await site.start()

        logger.info(
            "MADRAC MCP HTTP server listening on http://%s:%d", HOST, PORT
        )
        logger.info(
            "Auth token at: %s", get_token_path()
        )

    async def stop(self) -> None:
        """Stop the HTTP server."""
        if self._runner:
            await self._runner.cleanup()
            logger.info("MADRAC MCP HTTP server stopped")

    @web.middleware
    async def _auth_middleware(
        self,
        request: web.Request,
        handler,
    ) -> web.Response:
        """Validate Bearer token on all requests except /health."""
        if request.path == "/health":
            return await handler(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return web.Response(
                status=401,
                text=json.dumps({"error": "Missing Bearer token"}),
                content_type="application/json",
            )

        provided = auth[len("Bearer "):]
        if not validate_token(provided):
            logger.warning("MCP HTTP: invalid token from %s", request.remote)
            return web.Response(
                status=403,
                text=json.dumps({"error": "Invalid token"}),
                content_type="application/json",
            )

        return await handler(request)

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Health check — no auth required."""
        from .tool_schemas import MADRAC_TOOL_SCHEMAS
        return web.Response(
            text=json.dumps({
                "status": "ok",
                "server": "madrac-subs",
                "tools": len(MADRAC_TOOL_SCHEMAS),
                "resources": 4,
            }),
            content_type="application/json",
        )

    async def _handle_list_tools(
        self, request: web.Request
    ) -> web.Response:
        """List available tools — auth required."""
        from .tool_schemas import MADRAC_TOOL_SCHEMAS
        return web.Response(
            text=json.dumps({"tools": MADRAC_TOOL_SCHEMAS}),
            content_type="application/json",
        )

    async def _handle_mcp(self, request: web.Request) -> web.Response:
        """
        Handle MCP JSON-RPC requests.
        Routes to the appropriate tool or resource.
        """
        try:
            body = await request.json()
        except Exception as e:
            return web.Response(
                status=400,
                text=json.dumps({"error": f"Invalid JSON: {e}"}),
                content_type="application/json",
            )

        method = body.get("method", "")
        params = body.get("params", {})
        req_id = body.get("id", 1)

        result = await self._dispatch(method, params)

        return web.Response(
            text=json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result,
            }),
            content_type="application/json",
        )

    async def _dispatch(
        self, method: str, params: dict
    ) -> Any:
        """Route method to the correct tool or resource."""
        if method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            return await self._call_tool(tool_name, arguments)

        if method == "tools/list":
            from .tool_schemas import MADRAC_TOOL_SCHEMAS
            return {"tools": MADRAC_TOOL_SCHEMAS}

        if method == "resources/read":
            uri = params.get("uri", "")
            return await self._read_resource(uri)

        return {"error": f"Unknown method: {method}"}

    async def _call_tool(
        self, name: str, arguments: dict
    ) -> Any:
        """Call a registered MCP tool by name."""
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
        from .tools.recon_map import map_speakers_to_segments

        tool_map = {
            "get_queue_status": get_queue_status(self.app_state),
            "pause_processing": pause_processing(self.app_state),
            "resume_processing": resume_processing(self.app_state),
            "transcribe_file": transcribe_file(self.app_state),
            "translate_subtitles": translate_subtitles(self.app_state),
            "execute_assistant_action": execute_assistant_action(self.app_state),
            "read_config": read_config(self.app_state),
            "get_dubbing_status": get_dubbing_status(self.app_state),
            "start_dubbing": start_dubbing(self.app_state),
            "get_workspace_info": get_workspace_info(self.app_state),
            "list_workspaces": list_workspaces(self.app_state),
            "get_segments": get_segments(self.app_state),
            "rename_speaker": rename_speaker(self.app_state),
            "edit_subtitle_segment": edit_subtitle_segment(self.app_state),
            "export_srt": export_srt(self.app_state),
            "create_window": create_window(self.app_state),
            "update_widget": update_widget(self.app_state),
            "close_window": close_window(self.app_state),
            "list_windows": list_windows(self.app_state),
            "get_window_events": get_window_events(self.app_state),
            "diarize_speakers": diarize_speakers(self.app_state),
            "map_speakers_to_segments": map_speakers_to_segments(self.app_state),
        }

        if name not in tool_map:
            return {"error": f"Unknown tool: {name}"}

        try:
            fn = tool_map[name]
            return await fn(**arguments)
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e)
            return {"error": str(e)}

    async def _read_resource(self, uri: str) -> Any:
        """Read a registered MCP resource by URI.
        FUTURE_IMPROVEMENT: MUI events are exposed as a tool (get_window_events)
        in Phase 1. Migrate to a resource uri://events/<window_id> in Phase 2.
        """
        from .resources.queue import get_queue_estado_resource, get_queue_progreso_resource
        from .resources.config import get_config_actual_resource
        from .resources.logs import get_ultimos_logs_resource

        if uri == "queue://estado":
            handler = get_queue_estado_resource(self.app_state)
            result = await handler()
            return json.loads(result) if isinstance(result, str) else result
        if uri.startswith("queue://progreso/"):
            job_id = uri.split("/")[-1]
            handler = get_queue_progreso_resource(self.app_state, job_id)
            result = await handler()
            return json.loads(result) if isinstance(result, str) else result
        if uri == "config://actual":
            handler = get_config_actual_resource(self.app_state)
            result = await handler()
            return json.loads(result) if isinstance(result, str) else result
        if uri.startswith("log://ultimos/"):
            n = int(uri.split("/")[-1])
            handler = get_ultimos_logs_resource(self.app_state, n)
            result = await handler()
            return json.loads(result) if isinstance(result, str) else result

        return {"error": f"Unknown resource: {uri}"}


def run_http_server(app_state: dict[str, Any]) -> None:
    """Entry point for running the MCP HTTP server standalone."""

    async def _main():
        server = MCPHttpServer(app_state)
        await server.start()
        logger.info("Press Ctrl+C to stop")
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, asyncio.CancelledError):
            await server.stop()

    asyncio.run(_main())