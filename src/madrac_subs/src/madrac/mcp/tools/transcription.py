"""Transcription MCP tools."""
from __future__ import annotations
from typing import Any


def transcribe_file(app_state: dict[str, Any]):
    async def _transcribe_file(ruta: str, idioma: str = "es") -> str:
        """
        Transcribe an audio or video file using faster-whisper.

        Args:
            ruta: Absolute path to the audio/video file
            idioma: Language code (e.g. 'es', 'en', 'fr'). Default: 'es'

        Returns:
            Path to the generated .srt file, or error message.
        """
        qm = app_state.get("queue_manager")
        if qm is None:
            return "Error: queue_manager not available"
        try:
            job_id = qm.add_file(ruta, idioma=idioma)
            return f"Transcription queued. Job ID: {job_id}"
        except Exception as e:
            return f"Error queuing transcription: {e}"
    return _transcribe_file
