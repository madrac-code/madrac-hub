"""PipelineWorker: orchestrates stages as a QThread with Qt signals.

Collects StageMetrics per item and emits PipelineMetrics on completion.
"""

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..config import get_config
from ..core import get_logger, get_bus as get_event_bus
from ..supabase_client import CLIENTE
from ..utils.hashing import sha256 as compute_sha256
from ..utils.ffmpeg import get_duration as _get_duration
from .queue import ProcessingState
from .stages.metrics import MetricsCollector

logger = get_logger("pipeline.worker")

MAX_ACTIVE_PIPELINES = 1

try:
    from PySide6.QtCore import QThread, Signal
    HAS_QT = True
except ImportError:
    HAS_QT = False
    class QThread:
        pass
    class Signal:
        def __init__(self, *args: Any) -> None:
            self._args = args
        def __get__(self, obj: Any, objtype: Any) -> Any:
            return self


class PipelineWorker(QThread if HAS_QT else object):
    """Orchestrates pipeline stages in a worker thread.

    Emits Qt signals (when available) and EventBus events.
    """

    started = Signal(str)
    progress = Signal(str, float, str)
    log = Signal(str)
    finished = Signal(str, bool, str)
    all_completed = Signal()

    def __init__(self, parent: Any = None) -> None:
        if HAS_QT:
            super().__init__(parent)
        else:
            super().__init__()
        self._cancel_event = threading.Event()
        self._paused_event = threading.Event()
        self._paused_event.set()
        self._queue_manager: Any = None
        self._stages: List[Any] = []
        self._bus = get_event_bus()
        self._metrics = MetricsCollector()

    def set_queue(self, manager: Any) -> None:
        self._queue_manager = manager

    def set_stages(self, stages: List[Any]) -> None:
        self._stages = stages

    def cancel(self) -> None:
        self._cancel_event.set()

    def pause(self) -> None:
        self._paused_event.clear()

    def resume(self) -> None:
        self._paused_event.set()

    def _should_cancel(self) -> bool:
        return self._cancel_event.is_set()

    # ---- signal helpers ----

    def _emit_started(self, item_id: str) -> None:
        if HAS_QT:
            self.started.emit(item_id)
        self._bus.emit("worker.started", {"id": item_id})

    def _emit_progress(self, item_id: str, pct: float, stage: str) -> None:
        if HAS_QT:
            self.progress.emit(item_id, pct, stage)
        self._bus.emit("worker.progress", {"id": item_id, "progress": pct, "stage": stage})

    def _emit_log(self, msg: str) -> None:
        if HAS_QT:
            self.log.emit(msg)
        self._bus.emit("worker.log", {"message": msg})

    def _emit_finished(self, item_id: str, success: bool, error: str = "") -> None:
        if HAS_QT:
            self.finished.emit(item_id, success, error)
        self._bus.emit("worker.finished", {"id": item_id, "success": success, "error": error})

    def _emit_metrics(self, metrics_json: str) -> None:
        self._bus.emit("worker.metrics", {"metrics": metrics_json})

    # ---- main loop ----

    def run(self) -> None:
        logger.info("Worker started (max_active=%d)", MAX_ACTIVE_PIPELINES)
        self._bus.emit("worker.state", {"state": "running", "max_active": MAX_ACTIVE_PIPELINES})

        try:
            while not self._cancel_event.is_set():
                self._paused_event.wait()

                next_item = self._queue_manager.next_pending() if self._queue_manager else None
                if not next_item:
                    break

                self._process_item(next_item)

            self._bus.emit("worker.state", {"state": "idle"})
            if HAS_QT:
                self.all_completed.emit()
            logger.info("Worker finished")

        except Exception as e:
            logger.exception("Worker crashed: %s", e)
            self._bus.emit("worker.crash", {"error": str(e)})

    def _process_item(self, item: Any) -> None:
        item_id = item.id
        self._queue_manager.set_state(item_id, ProcessingState.PROCESSING)
        self._emit_started(item_id)

        context: Dict[str, Any] = {"ruta": item.ruta}
        success = False
        error_msg = ""

        # Start metrics collection for this item
        self._metrics.reset(item_id)

        # ── Community pre-check (antes de stages) ─────────────
        auto_buscar = get_config("comunidad.auto_buscar", True)
        auto_descargar = get_config("comunidad.auto_descargar", True)
        if (
            get_config("comunidad.habilitado", False)
            and auto_buscar
            and CLIENTE.is_logged_in()
        ):
            path_video = Path(item.ruta)
            self._emit_log("Buscando en comunidad...")
            duration_s = _get_duration(item.ruta)
            context["duration_s"] = duration_s
            video_hash = compute_sha256(path_video)
            if video_hash:
                context["video_hash"] = video_hash
                idioma_busqueda = get_config("traduccion.idioma_destino", "es")
                matches = CLIENTE.buscar_por_hash(
                    video_hash, idioma=idioma_busqueda,
                    duracion_seg=duration_s,
                    tolerancia_seg=3.0,
                )
                if matches and auto_descargar:
                    best = matches[0]
                    destino = path_video.parent / f"{path_video.stem}.srt"
                    ok = CLIENTE.descargar_subtitulo(best["id"], destino)
                    if ok:
                        self._queue_manager.update(item_id,
                            output_path=str(destino),
                            metadata={**item.metadata,
                                "share_candidate": True,
                                "video_hash": video_hash,
                                "community_subtitle_id": best["id"],
                            },
                        )
                        self._queue_manager.set_state(item_id, ProcessingState.COMPLETED)
                        self._emit_log(f"[OK] Descargado de comunidad: {destino.name}")
                        self._emit_finished(item_id, True, "")
                        self._emit_log("[OK] Pipeline complete")
                        self._save_metrics(self._metrics.build(duration_s))
                        return
                    else:
                        self._emit_log("[WARN] Fallo descarga de comunidad, usando Whisper")

        for stage in self._stages:
            if self._cancel_event.is_set():
                error_msg = "Cancelled"
                break

            self._metrics.stage_start(stage.name)
            self._emit_progress(item_id, 0.0, stage.name)
            self._emit_log(f"[{stage.name}] Starting...")

            result = stage.execute(
                item_id=item_id,
                context=context,
                on_progress=lambda i, p, s: self._on_stage_progress(i, p, s),
                on_log=self._emit_log,
                should_cancel=lambda: self._cancel_event.is_set(),
            )
            self._metrics.stage_end()

            if not result.success:
                error_msg = result.error or f"{stage.name} failed"
                self._emit_log(f"[FAIL] {error_msg}")
                stage.rollback(context)
                break

            self._emit_log(f"[OK] {stage.name} complete")
        else:
            success = True
            output = (
                context.get("muxed_path")
                or context.get("subtitle_path")
                or context.get("output_path")
                or context.get("embedded_subs_path", "")
            )
            if output:
                self._queue_manager.update(item_id, output_path=output)
            self._queue_manager.update(item_id, metadata={
                **item.metadata,
                "share_candidate": True,
                "video_hash": context.get("video_hash", ""),
            })
            self._emit_log("[OK] Pipeline complete")

        if self._cancel_event.is_set() and not error_msg:
            error_msg = "Cancelled"

        final_state = ProcessingState.COMPLETED if success else (
            ProcessingState.CANCELLED if self._cancel_event.is_set() else ProcessingState.FAILED
        )
        self._queue_manager.set_state(item_id, final_state, error=error_msg if not success else None)
        self._emit_finished(item_id, success, error_msg)

        # Build and emit metrics
        audio_dur = context.get("duration_s", 0.0)
        pipeline_metrics = self._metrics.build(audio_dur)
        log_line = self._metrics.format_log(pipeline_metrics)
        logger.info("Pipeline metrics [%s]: %s", item_id, log_line)
        self._emit_log(f"[METRICS] {log_line}")

        # Persist metrics to profile.json
        self._save_metrics(pipeline_metrics)

        # Emit structured metrics event
        import json as _json
        self._emit_metrics(_json.dumps(self._metrics.to_dict(pipeline_metrics)))

        # Cleanup stages (release models, GPU memory, etc.)
        for stage in self._stages:
            try:
                stage.cleanup()
            except Exception as e:
                logger.warning("Stage.cleanup() error [%s]: %s", stage.name, e)

    def _save_metrics(self, metrics: Any) -> None:
        """Append metrics to profile.json in cache dir."""
        try:
            from ..core.paths import get_user_data_dir
            from ..core import read_json, write_json
            profile_path = get_user_data_dir() / "profile.json"
            data = self._metrics.to_dict(metrics)
            if profile_path.exists():
                try:
                    existing = read_json(profile_path)
                    if isinstance(existing, list):
                        existing.append(data)
                    else:
                        existing = [existing, data]
                except Exception:
                    existing = [data]
            else:
                existing = [data]
            write_json(profile_path, existing)
        except Exception as e:
            logger.debug("Could not save profile.json: %s", e)

    def _on_stage_progress(self, item_id: str, progress: float, stage: str) -> None:
        self._queue_manager.set_progress(item_id, progress, stage)
        self._emit_progress(item_id, progress, stage)


Worker = PipelineWorker
