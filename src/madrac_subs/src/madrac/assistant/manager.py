import sys
import threading
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

from ..core import get_logger

logger = get_logger("assistant.manager")

_ASSISTANT_BASE: Optional[Path] = None


def _ensure_importable():
    global _ASSISTANT_BASE
    if _ASSISTANT_BASE is not None:
        return
    if getattr(sys, "frozen", False):
        _ASSISTANT_BASE = Path(sys._MEIPASS) / "madrac_asistente"
        return
    root = Path(__file__).resolve().parents[4]
    base = root / "madrac_asistente"
    if base.is_dir():
        sys.path.insert(0, str(base))
        _ASSISTANT_BASE = base
    else:
        raise RuntimeError(f"madrac_asistente not found at {base}")


class AssistantManager(QObject):
    state_changed = Signal(bool)
    error_occurred = Signal(str)
    log_message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self):
        if self._running:
            logger.warning("Assistant already running")
            return
        try:
            _ensure_importable()
        except RuntimeError as e:
            self.error_occurred.emit(str(e))
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if not self._running:
            return
        logger.info("Stopping assistant...")
        self._stop_event.set()
        self._detener_ollama()
        self._thread = None
        self._running = False
        self.state_changed.emit(False)
        logger.info("Assistant stopped")

    def _run(self):
        logger.info("Assistant starting...")
        self._running = True
        self.state_changed.emit(True)
        try:
            import asistente
            asistente._iniciar_ollama()
            if not asistente.inicializar_sistema():
                raise RuntimeError("Assistant initialization failed")
            self.log_message.emit("Assistant ready")
            asistente.loop_principal(stop_event=self._stop_event)
        except Exception as e:
            self.error_occurred.emit(str(e))
            logger.error("Assistant error: %s", e, exc_info=True)
        finally:
            try:
                import asistente
                asistente._detener_ollama()
            except Exception:
                pass
            self._running = False
            self.state_changed.emit(False)
            self.log_message.emit("Assistant stopped")
            logger.info("Assistant loop ended")

    def _detener_ollama(self):
        try:
            import asistente
            asistente._detener_ollama()
        except Exception:
            pass
