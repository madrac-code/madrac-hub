"""RECON Character Identity MCP tools — speaker_id → character_id mapping."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# madrac_recon lives at the monorepo src/ root (sibling of madrac_subs).
_SRC_ROOT = Path(__file__).resolve().parents[5]
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from madrac.workspace.shared import SharedWorkspace  # noqa: E402


def _validate_job(ws: SharedWorkspace, job_id: str) -> dict[str, Any] | None:
    """Validate workspace exists and has speakers.json. Returns error dict or None."""
    if not (ws.root / "metadata.json").exists():
        return {"error": f"Workspace not found: {job_id}"}
    if not (ws.root / "speakers.json").exists():
        return {"error": f"speakers.json not found in job {job_id} — run diarize_speakers first"}
    return None


def _load_speakers(ws: SharedWorkspace) -> dict[str, Any]:
    """Load speakers.json, return parsed data."""
    path = ws.root / "speakers.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_characters(ws: SharedWorkspace) -> list[dict[str, Any]]:
    """Load characters.json, return list (empty if not exists)."""
    chars = ws.load_characters()
    return chars if chars is not None else []


def _save_characters(ws: SharedWorkspace, characters: list[dict[str, Any]]) -> None:
    """Save characters to workspace."""
    ws.save_characters(characters)


def _speaker_exists(speakers_data: dict[str, Any], speaker_id: str) -> bool:
    """Check if speaker_id exists in speakers.json."""
    return any(s["speaker_id"] == speaker_id for s in speakers_data.get("speakers", []))


def _character_exists(characters: list[dict[str, Any]], character_id: str) -> bool:
    """Check if character_id exists."""
    return any(c["character_id"] == character_id for c in characters)


def _get_character(characters: list[dict[str, Any]], character_id: str) -> dict[str, Any] | None:
    """Get character by ID."""
    for c in characters:
        if c["character_id"] == character_id:
            return c
    return None


import json


def list_characters(app_state: dict[str, Any]):
    """List all characters in a workspace with their current speaker mapping."""
    async def _list_characters(job_id: str) -> dict[str, Any]:
        try:
            ws = SharedWorkspace.from_job_id(job_id)
            err = _validate_job(ws, job_id)
            if err:
                return err
            characters = _load_characters(ws)
            return {
                "job_id": job_id,
                "characters": [
                    {
                        "character_id": c["character_id"],
                        "name": c["name"],
                        "speaker_id": c.get("speaker_id"),
                        "visual_reference": c.get("visual_reference"),
                        "notes": c.get("notes", ""),
                    }
                    for c in characters
                ],
                "count": len(characters),
            }
        except FileNotFoundError:
            return {"error": f"Workspace not found: {job_id}"}
        except Exception as e:
            return {"error": str(e)}
    return _list_characters


def set_character(app_state: dict[str, Any]):
    """Create or update a character in the workspace."""
    async def _set_character(
        job_id: str,
        character_id: str,
        name: str,
        visual_reference: str | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        try:
            ws = SharedWorkspace.from_job_id(job_id)
            err = _validate_job(ws, job_id)
            if err:
                return err
            if not character_id or not character_id.strip():
                return {"error": "character_id required"}
            if not name or not name.strip():
                return {"error": "name required"}

            characters = _load_characters(ws)
            existing = _get_character(characters, character_id)

            if existing:
                # Update existing
                existing["name"] = name
                existing["visual_reference"] = visual_reference
                existing["notes"] = notes
                # Keep existing speaker_id if not provided in update
            else:
                # Create new
                characters.append({
                    "character_id": character_id,
                    "name": name,
                    "speaker_id": None,
                    "visual_reference": visual_reference,
                    "notes": notes,
                })

            _save_characters(ws, characters)
            return {
                "job_id": job_id,
                "status": "done",
                "character_id": character_id,
                "name": name,
                "speaker_id": existing.get("speaker_id") if existing else None,
                "visual_reference": visual_reference,
                "notes": notes,
            }
        except FileNotFoundError:
            return {"error": f"Workspace not found: {job_id}"}
        except Exception as e:
            return {"error": str(e)}
    return _set_character


def map_speaker_to_character(app_state: dict[str, Any]):
    """Map a speaker to a character (links acoustic to narrative identity)."""
    async def _map_speaker_to_character(
        job_id: str,
        speaker_id: str,
        character_id: str,
    ) -> dict[str, Any]:
        try:
            ws = SharedWorkspace.from_job_id(job_id)
            err = _validate_job(ws, job_id)
            if err:
                return err

            speakers_data = _load_speakers(ws)
            if not _speaker_exists(speakers_data, speaker_id):
                return {"error": f"Speaker not found: {speaker_id}"}

            characters = _load_characters(ws)
            if not _character_exists(characters, character_id):
                return {"error": f"Character not found: {character_id}"}

            # Check if speaker already mapped to another character
            for c in characters:
                if c.get("speaker_id") == speaker_id and c["character_id"] != character_id:
                    # Unassign from previous character
                    c["speaker_id"] = None

            # Assign speaker to character
            target = _get_character(characters, character_id)
            if not target:
                return {"error": f"Character not found: {character_id}"}
            target["speaker_id"] = speaker_id

            _save_characters(ws, characters)

            # Get speaker name for response
            speaker_name = next(
                (s["name"] for s in speakers_data.get("speakers", []) if s["speaker_id"] == speaker_id),
                speaker_id,
            )

            return {
                "job_id": job_id,
                "status": "done",
                "speaker_id": speaker_id,
                "speaker_name": speaker_name,
                "character_id": character_id,
                "character_name": target["name"],
            }
        except FileNotFoundError:
            return {"error": f"Workspace not found: {job_id}"}
        except Exception as e:
            return {"error": str(e)}
    return _map_speaker_to_character


def register(mcp):
    """Register Character Identity MCP tools."""
    mcp.tool(
        name="list_characters",
        description="List all characters in a workspace with their current speaker mapping.",
    )(list_characters({}))

    mcp.tool(
        name="set_character",
        description="Create or update a character (narrative identity). "
                    "speaker_id is optional and managed via map_speaker_to_character.",
    )(set_character({}))

    mcp.tool(
        name="map_speaker_to_character",
        description="Map a diarized speaker (acoustic identity) to a character (narrative identity).",
    )(map_speaker_to_character({}))