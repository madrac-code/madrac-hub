"""
MADRAC MCP HTTP Server launcher.

Usage:
  python run_mcp_http.py

Starts the MCP HTTP server on http://127.0.0.1:7654
Auth token written to: ~/.cache/madrac-subs/mcp_token.txt

External agents connect with:
  Authorization: Bearer <token from token file>
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from madrac.mcp.http_server import run_http_server
from madrac.mcp.auth import get_token_path

app_state: dict = {}

if __name__ == "__main__":
    print(f"MADRAC MCP HTTP Server starting on http://127.0.0.1:7654")
    print(f"Token file: {get_token_path()}")
    print(f"Health check: http://127.0.0.1:7654/health (no auth)")
    run_http_server(app_state)