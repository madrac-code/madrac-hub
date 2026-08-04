"""
MADRAC MCP Agent Client.

Helper for external agents (OpenCode, scripts, MADRAC-CORE components)
to connect to the MCP HTTP server.

Usage:
    from madrac.mcp.agent_client import MADRACAgent

    agent = MADRACAgent()  # reads token automatically
    status = agent.call_tool("get_queue_status")
    tools = agent.list_tools()
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TOKEN_PATH = Path.home() / ".cache" / "madrac-subs" / "mcp_token.txt"
DEFAULT_URL = "http://127.0.0.1:7654"


class MADRACAgent:
    """
    Simple client for connecting to the MADRAC MCP HTTP server.
    Reads auth token from the standard token file.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_URL,
        token_path: Path = TOKEN_PATH,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = self._load_token(token_path)

    def _load_token(self, path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(
                f"MCP token not found at {path}. "
                "Is the MADRAC MCP HTTP server running?"
            )
        return path.read_text().strip()

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def health(self) -> dict:
        """Check server health (no auth required)."""
        import urllib.request
        with urllib.request.urlopen(f"{self.base_url}/health") as r:
            return json.loads(r.read())

    def list_tools(self) -> list[dict]:
        """List all available MCP tools."""
        return self._request("tools/list", {}).get("tools", [])

    def call_tool(self, name: str, **kwargs) -> Any:
        """
        Call an MCP tool by name with keyword arguments.

        Examples:
            agent.call_tool("get_queue_status")
            agent.call_tool("transcribe_file", ruta="/videos/test.mp4")
            agent.call_tool("execute_assistant_action", accion="obtener_hora")
        """
        return self._request("tools/call", {
            "name": name,
            "arguments": kwargs,
        })

    def read_resource(self, uri: str) -> Any:
        """
        Read an MCP resource by URI.

        Examples:
            agent.read_resource("queue://estado")
            agent.read_resource("queue://progreso/job_001")
            agent.read_resource("config://actual")
            agent.read_resource("log://ultimos/20")
        """
        return self._request("resources/read", {"uri": uri})

    def _request(self, method: str, params: dict) -> Any:
        """Send a JSON-RPC request to the MCP HTTP server."""
        import urllib.request
        import urllib.error

        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/mcp",
            data=payload,
            headers=self._headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                response = json.loads(r.read())
                if "error" in response:
                    raise RuntimeError(
                        f"MCP error: {response['error']}"
                    )
                return response.get("result")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            raise RuntimeError(f"HTTP {e.code}: {body}") from e