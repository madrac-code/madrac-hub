"""Transcription MCP tools — queues files via QueueManager."""
from __future__ import annotations
from typing import Any


def transcribe_file(app_state: dict[str, Any]):
    async def _transcribe_file(ruta: str, idioma: str = "es") -> str:
        """
        Transcribe an audio or video file. Queues the file for processing.

        Args:
            ruta: Absolute path to the audio/video file
            idioma: Language code (e.g. 'es', 'en', 'fr'). Default: 'es'

        Returns:
            Job ID for the queued transcription, or error message.
        """
        qm = app_state.get("queue_manager")
        if qm is None:
            return "Error: queue_manager not available"
        try:
            from pathlib import Path
            path = Path(ruta)
            if not path.exists():
                return f"Error: file not found: {ruta}"
            entry = qm.add(ruta)
            worker = app_state.get("worker")
            if worker is not None and hasattr(worker, "isRunning"):
                if not worker.isRunning():
                    worker.start()
                    return (
                        f"Transcription queued. Job ID: {entry.id} "
                        f"(worker auto-started)"
                    )
            return f"Transcription queued. Job ID: {entry.id}"
        except Exception as e:
            return f"Error queuing transcription: {e}"
    return _transcribe_file
