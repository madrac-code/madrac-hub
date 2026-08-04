"""
MCP HTTP auth — local token management.

Token is stored at ~/.cache/madrac-subs/mcp_token.txt
Generated at server start if not exists.
Agents on the same machine read this file to authenticate.
"""
from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)

TOKEN_PATH = Path.home() / ".cache" / "madrac-subs" / "mcp_token.txt"
TOKEN_LENGTH = 32  # bytes → 64 hex chars


def get_or_create_token() -> str:
    """
    Return the current MCP auth token.
    Creates a new one if none exists.
    """
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)

    if TOKEN_PATH.exists():
        token = TOKEN_PATH.read_text().strip()
        if token:
            logger.info("MCP token loaded from %s", TOKEN_PATH)
            return token

    token = secrets.token_hex(TOKEN_LENGTH)
    TOKEN_PATH.write_text(token)
    TOKEN_PATH.chmod(0o600)
    logger.info("MCP token created at %s", TOKEN_PATH)
    return token


def get_token_path() -> Path:
    """Return the path where agents should read the token."""
    return TOKEN_PATH


def validate_token(provided: str) -> bool:
    """Constant-time token comparison to prevent timing attacks."""
    expected = TOKEN_PATH.read_text().strip() if TOKEN_PATH.exists() else ""
    return secrets.compare_digest(provided, expected)


def revoke_token() -> None:
    """Delete the current token. Next start will generate a new one."""
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
        logger.info("MCP token revoked")