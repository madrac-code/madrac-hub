"""MCP tool: map_speakers_to_segments (RECON Phase 2)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# madrac_recon lives at the monorepo src/ root (sibling of madrac_subs).
_SRC_ROOT = Path(__file__).resolve().parents[5]
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from mcp.server.fastmcp import FastMCP
from madrac_recon import map_job  # noqa: E402


def map_speakers_to_segments(app_state: dict[str, Any]):
    """Map diarized speakers to subtitle segments by temporal overlap."""
    async def _map_speakers_to_segments(job_id: str | None = None) -> dict[str, Any]:
        """
        Assign each subtitle segment to the speaker with maximum temporal overlap.

        Args:
            job_id: Workspace job ID (sha256-<hex>). Must have both segments.json
                    (from SUBS transcription) and speakers.json (from diarize_speakers).

        Returns:
            Dict with mapped_count, unmapped, total_confidence, and output path.
        """
        if not job_id:
            return {"error": "Provide job_id"}
        return map_job(job_id)

    return _map_speakers_to_segments


def register(mcp: FastMCP) -> None:
    """Register the map_speakers_to_segments tool."""
    mcp.tool(
        name="map_speakers_to_segments",
        description="Map diarized speakers to subtitle segments by temporal overlap.",
    )(map_speakers_to_segments({}))