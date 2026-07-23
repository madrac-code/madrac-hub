"""Dubbing MCP tools."""
from __future__ import annotations
from typing import Any


def get_dubbing_status(app_state: dict[str, Any]):
    async def _get_dubbing_status(job_id: str = "") -> dict:
        """
        Get the status of a dubbing job.

        Args:
            job_id: Job ID returned by start_dubbing. If empty,
                    returns status of all active jobs.

        Returns:
            dict with job status information.
        """
        dm = app_state.get("dubbing_manager")
        if dm is None:
            return {"error": "dubbing_manager not available"}
        return dm.get_status(job_id) if job_id else dm.get_all_status()
    return _get_dubbing_status


def start_dubbing(app_state: dict[str, Any]):
    async def _start_dubbing(video_path: str, idioma: str = "es") -> str:
        """
        Start a dubbing job for a video file.

        Args:
            video_path: Absolute path to the video file
            idioma: Target language for dubbing (default: 'es')

        Returns:
            Job ID string, or error message.
        """
        dm = app_state.get("dubbing_manager")
        if dm is None:
            return "Error: dubbing_manager not available"
        try:
            job_id = dm.start_job(video_path, idioma)
            return f"Dubbing started. Job ID: {job_id}"
        except Exception as e:
            return f"Error starting dubbing: {e}"
    return _start_dubbing
