"""Queue management MCP tools."""
from __future__ import annotations
from typing import Any


def get_queue_status(app_state: dict[str, Any]):
    async def _get_queue_status() -> dict:
        """
        Get the current state of the processing queue.

        Returns:
            dict with keys: pendientes (int), en_progreso (int),
            completados (int), total (int)
        """
        qm = app_state.get("queue_manager")
        if qm is None:
            return {"error": "queue_manager not available"}
        return {
            "pendientes": qm.pending_count(),
            "en_progreso": qm.active_count(),
            "completados": qm.completed_count(),
            "total": qm.total_count(),
        }
    return _get_queue_status


def pause_processing(app_state: dict[str, Any]):
    async def _pause_processing() -> bool:
        """
        Pause the processing queue. Returns True if paused successfully.
        """
        qm = app_state.get("queue_manager")
        if qm is None:
            return False
        qm.pause()
        return True
    return _pause_processing
