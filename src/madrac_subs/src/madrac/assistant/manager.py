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
    root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent
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
        self._ollama_process = None

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
            import core
            from core import cargar_config, logger as as_logger
            from historial import HistorialConversacion
            from asistente import _iniciar_ollama, inicializar_sistema

            _iniciar_ollama()
            if not inicializar_sistema():
                self.error_occurred.emit("Assistant initialization failed")
                self._running = False
                self.state_changed.emit(False)
                return

            config = cargar_config()
            historial = HistorialConversacion(max_tamano=10)

            from asistente import (
                _detener_ollama,
                esperar_wakeword,
                grabar_audio,
                transcribir,
                consultar_ia,
                ejecutar_accion,
                hablar,
                logger,
            )

            self._ollama_process = True
            hablar("Asistente iniciado")
            self.log_message.emit("Assistant ready. Say hey Jarvis to activate.")

            while not self._stop_event.is_set():
                try:
                    from asistente import esperar_wakeword

                    if not self._esperar_wakeword_con_stop():
                        continue

                    self.log_message.emit("Wake word detected")

                    hablar("Si?")
                    config = cargar_config()
                    audio_cmd = grabar_audio(segundos=config["audio"]["duracion_grabacion"])

                    if self._stop_event.is_set():
                        break

                    comando = transcribir(audio_cmd)

                    if self._stop_event.is_set():
                        break

                    if comando:
                        accion, parametro, es_comando = consultar_ia(comando, historial)
                        self.log_message.emit(f"Action: {accion} | Param: {parametro}")

                        if es_comando:
                            historial.limpiar()

                        exito, mensaje = ejecutar_accion(accion, parametro)
                        hablar(mensaje)
                    else:
                        hablar("No entendi, intenta de nuevo.")

                except Exception as e:
                    logger.error(f"Error in assistant loop: {e}")
                    if self._stop_event.is_set():
                        break

        except Exception as e:
            self.error_occurred.emit(f"Assistant error: {e}")
            logger.error(f"Assistant fatal: {e}", exc_info=True)
        finally:
            self._detener_ollama()
            self._running = False
            self.state_changed.emit(False)
            self.log_message.emit("Assistant stopped")
            logger.info("Assistant loop ended")

    def _esperar_wakeword_con_stop(self):
        import sounddevice as sd
        import numpy as np
        from openwakeword.model import Model as WakeModel
        from core import cargar_config

        config = cargar_config()
        sample_rate = config["audio"]["sample_rate"]
        chunk_size = config["audio"]["chunk_size"]
        device = config["audio"]["dispositivo_mic"]
        modelo_path = config["wakeword"]["modelo"]
        umbral = config["wakeword"]["umbral"]

        wake_model = WakeModel(
            wakeword_models=[modelo_path],
            inference_framework=config["wakeword"]["framework"]
        )
        wake_model.reset()

        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            device=device,
            blocksize=chunk_size,
        ) as stream:
            while not self._stop_event.is_set():
                chunk, _ = stream.read(chunk_size)
                chunk_np = np.squeeze(chunk)
                prediccion = wake_model.predict(chunk_np)
                score = list(prediccion.values())[0]
                if score >= umbral:
                    return True
        return False

    def _ollama_responde(self):
        try:
            import urllib.request
            urllib.request.urlopen("http://127.0.0.1:11434", timeout=2)
            return True
        except Exception:
            return False

    def _detener_ollama(self):
        pass
