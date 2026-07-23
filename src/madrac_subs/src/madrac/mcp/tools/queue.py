"""Queue management MCP tools — real QueueManager + PipelineWorker integration."""
from __future__ import annotations
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from madrac.pipeline.queue import ProcessingState as _PS


def get_queue_status(app_state: dict[str, Any]):
    async def _get_queue_status() -> dict:
        """
        Get the current state of the processing queue.

        Returns:
            dict with keys: pendientes (int), en_progreso (int),
            completados (int), fallidos (int), total (int)
        """
        qm = app_state.get("queue_manager")
        if qm is None:
            return {"error": "queue_manager not available"}
        try:
            from madrac.pipeline.queue import ProcessingState
            all_items = qm.list_all()
            pendientes = sum(1 for e in all_items if e.state == ProcessingState.PENDING)
            en_progreso = sum(1 for e in all_items if e.state == ProcessingState.PROCESSING)
            completados = sum(1 for e in all_items if e.state == ProcessingState.COMPLETED)
            fallidos = sum(1 for e in all_items if e.state == ProcessingState.FAILED)
            return {
                "pendientes": pendientes,
                "en_progreso": en_progreso,
                "completados": completados,
                "fallidos": fallidos,
                "total": len(all_items),
            }
        except Exception as e:
            return {"error": str(e)}
    return _get_queue_status


def pause_processing(app_state: dict[str, Any]):
    async def _pause_processing() -> bool:
        """
        Pause the processing pipeline. Returns True if paused successfully.
        """
        worker = app_state.get("worker")
        if worker is None:
            return False
        worker.pause()
        return True
    return _pause_processing


def resume_processing(app_state: dict[str, Any]):
    async def _resume_processing() -> bool:
        """
        Resume the processing pipeline. Returns True if resumed successfully.
        """
        worker = app_state.get("worker")
        if worker is None:
            return False
        worker.resume()
        return True
    return _resume_processing
