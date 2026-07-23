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

    def execute_action(self, accion: str, parametro: str = "") -> Optional[str]:
        """Execute a named assistant action via the running asistente module."""
        if not self._running:
            return None
        try:
            import asistente
            handler = getattr(asistente, f"ejecutar_{accion}", None)
            if handler is None:
                handler = getattr(asistente, accion, None)
            if handler is None:
                logger.warning("Unknown assistant action: %s", accion)
                return None
            return handler(parametro) if parametro else handler()
        except Exception as e:
            logger.error("execute_action error: %s", e)
            return str(e)

    def start_mcp_server(
        self,
        queue_manager: Any = None,
        worker: Any = None,
        dubbing_manager: Any = None,
    ) -> None:
        """Start the MCP server in a background thread (stdio transport).

        Uses provided managers or discovers singletons from the codebase.
        The server runs until stdin closes or the process exits.
        """
        if getattr(self, "_mcp_thread", None) and self._mcp_thread.is_alive():
            logger.warning("MCP server already running")
            return

        from ..config import get_config_manager
        from collections import deque
        import logging as _logging

        log_buffer: deque[dict[str, str]] = deque(maxlen=1000)
        state: dict[str, Any] = {
            "queue_manager": queue_manager,
            "worker": worker,
            "config_manager": get_config_manager(),
            "dubbing_manager": dubbing_manager,
            "assistant_manager": self,
            "log_buffer": log_buffer,
        }
        # Capture madrac logs into the ring buffer
        _buf_handler = _logging.Handler()
        _buf_handler.emit = lambda r: log_buffer.append({
            "time": _logging.Formatter().formatTime(r),
            "level": r.levelname,
            "name": r.name,
            "message": r.getMessage(),
        })
        _buf_handler.setLevel(_logging.DEBUG)
        _logging.getLogger("madrac").addHandler(_buf_handler)

        from ..mcp.server import run_server

        self._mcp_thread = threading.Thread(
            target=run_server,
            args=(state,),
            daemon=True,
            name="mcp-stdio",
        )
        self._mcp_thread.start()
        logger.info("MCP server thread started (stdio)")

    def stop_mcp_server(self) -> None:
        """Signal the MCP server to stop. For stdio transport, closing
        stdin is the cleanest approach; daemon thread suffices otherwise."""
        thread = getattr(self, "_mcp_thread", None)
        if thread and thread.is_alive():
            logger.info("MCP server thread will exit on daemon shutdown")
        self._mcp_thread = None

    def _detener_ollama(self):
        try:
            import asistente
            asistente._detener_ollama()
        except Exception:
            pass
