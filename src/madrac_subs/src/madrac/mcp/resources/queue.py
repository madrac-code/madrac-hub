"""Queue state MCP resources — real QueueManager integration.

Resources:
    queue://estado          — summary with counts + recent items
    queue://progreso/{id}   — single item progress
"""
from __future__ import annotations
import json
from typing import Any


def get_queue_estado_resource(app_state: dict[str, Any]):
    async def _handler() -> str:
        """queue://estado — full queue summary."""
        qm = app_state.get("queue_manager")
        if qm is None:
            return json.dumps({"error": "queue_manager not available"}, ensure_ascii=False)
        try:
            from madrac.pipeline.queue import ProcessingState
            all_items = qm.list_all()
            pendientes = sum(1 for e in all_items if e.state == ProcessingState.PENDING)
            en_progreso = sum(1 for e in all_items if e.state == ProcessingState.PROCESSING)
            completados = sum(1 for e in all_items if e.state == ProcessingState.COMPLETED)
            fallidos = sum(1 for e in all_items if e.state == ProcessingState.FAILED)
            items = [
                {
                    "id": e.id,
                    "state": e.state.name,
                    "filename": e.ruta,
                    "progress": e.progress,
                    "stage": e.stage,
                    "error": e.error,
                }
                for e in all_items[-20:]  # last 20 for brevity
            ]
            return json.dumps({
                "pendientes": pendientes,
                "en_progreso": en_progreso,
                "completados": completados,
                "fallidos": fallidos,
                "total": len(all_items),
                "items": items,
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    return _handler


def get_queue_progreso_resource(app_state: dict[str, Any]):
    async def _handler(job_id: str) -> str:
        """queue://progreso/{job_id} — single item progress."""
        qm = app_state.get("queue_manager")
        if qm is None:
            return json.dumps({"error": "queue_manager not available"}, ensure_ascii=False)
        try:
            all_items = qm.list_all()
            match = next((e for e in all_items if e.id == job_id), None)
            if match is None:
                return json.dumps({"error": f"job_id not found: {job_id}"}, ensure_ascii=False)
            return json.dumps({
                "id": match.id,
                "state": match.state.name,
                "filename": match.ruta,
                "progress_pct": match.progress,
                "stage": match.stage,
                "error": match.error,
                "output_path": match.output_path,
                "created_at": match.created_at,
                "updated_at": match.updated_at,
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    return _handler
