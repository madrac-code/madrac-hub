"""Dubbing MCP tools — real DubbingManager integration."""
from __future__ import annotations
from typing import Any
from pathlib import Path


def get_dubbing_status(app_state: dict[str, Any]):
    async def _get_dubbing_status(job_id: str = "") -> dict:
        """
        Get the status of a dubbing job via the DUBS subprocess API.

        Args:
            job_id: Job ID returned by start_dubbing. If empty,
                    returns a message indicating no job_id provided.

        Returns:
            dict with job status information from the DUBS API.
        """
        dm = app_state.get("dubbing_manager")
        if dm is None:
            return {"error": "dubbing_manager not available"}
        if not job_id:
            return {"message": "Provide a job_id to poll. Active jobs are managed by the DUBS subprocess."}
        try:
            return dm.poll_job(job_id)
        except Exception as e:
            return {"error": str(e)}
    return _get_dubbing_status


def start_dubbing(app_state: dict[str, Any]):
    async def _start_dubbing(
        video_path: str,
        srt_path: str,
        output_path: str = "",
        idioma: str = "es",
    ) -> str:
        """
        Start a dubbing job via the DUBS subprocess API.

        The DUBS subprocess is launched automatically if not already running.

        Args:
            video_path: Absolute path to the video file
            srt_path: Absolute path to the subtitle (.srt) file
            output_path: Optional output path for the dubbed video.
                         Auto-generated from video_path if empty.
            idioma: Target language for dubbing (default: 'es')

        Returns:
            Job ID string, or error message.
        """
        dm = app_state.get("dubbing_manager")
        if dm is None:
            return "Error: dubbing_manager not available"
        try:
            if not Path(video_path).exists():
                return f"Error: video not found: {video_path}"
            if not Path(srt_path).exists():
                return f"Error: srt not found: {srt_path}"
            if not output_path:
                video = Path(video_path)
                output_path = str(video.with_name(f"{video.stem}_dubbed_{idioma}{video.suffix}"))
            config = {"idioma": idioma}
            # Ensure DUBS subprocess is running
            if dm._process is None or dm._process.poll() is not None:
                ok = dm.launch_dubs()
                if not ok:
                    return "Error: failed to launch DUBS subprocess"
            job_id = dm.submit_job(video_path, srt_path, output_path, config)
            if job_id is None:
                return "Error: failed to submit dubbing job"
            return f"Dubbing started. Job ID: {job_id}"
        except Exception as e:
            return f"Error starting dubbing: {e}"
    return _start_dubbing
