"""CLI entry point for MADRAC MCP server (stdio transport).

Usage:
    python -m madrac.mcp
"""
from __future__ import annotations
from ..config import get_config_manager


def main() -> None:
    from .server import run_server
    from collections import deque
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    log_buffer: deque[dict[str, str]] = deque(maxlen=1000)
    buf_handler = logging.Handler()
    buf_handler.emit = lambda r: log_buffer.append({
        "time": logging.Formatter().formatTime(r),
        "level": r.levelname,
        "name": r.name,
        "message": r.getMessage(),
    })
    buf_handler.setLevel(logging.DEBUG)
    logging.getLogger("madrac").addHandler(buf_handler)

    state = {
        "queue_manager": None,
        "worker": None,
        "config_manager": get_config_manager(),
        "dubbing_manager": None,
        "assistant_manager": None,
        "log_buffer": log_buffer,
    }
    run_server(state)


if __name__ == "__main__":
    main()
