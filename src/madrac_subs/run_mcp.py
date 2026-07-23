"""MCP server launcher — adds src/ to sys.path, then starts the server.

Claude Desktop spawns this script directly (via configured venv python + cwd).
"""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(_SRC))

from madrac.mcp.__main__ import main

main()
