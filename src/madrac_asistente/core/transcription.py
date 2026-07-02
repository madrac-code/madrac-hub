# ────────────────────────────────────────────────────────────────────
# Transcripción
# ────────────────────────────────────────────────────────────────────
# Funciones para transcripción de audio usando Whisper.
# ────────────────────────────────────────────────────────────────────

import tempfile
import os
from typing import Tuple

from .config import cargar_config, logger
from .utils import obtener_ruta_recurso


def transcribir(audio: 'np.ndarray') -> str:
    """
    Transcribe audio usando Whisper.

    Args:
        audio (np.ndarray): datos de audio

    Returns:
        str: texto transcrito
    """
    import scipy.io.wavfile as wav
    from faster_whisper import WhisperModel

    config = cargar_config()
    modelo_whisper = config["whisper"]["modelo"]
    sample_rate = config["audio"]["sample_rate"]
    idioma = config["audio"]["idioma"]

    # Crear archivo temporal
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        # Guardar audio en archivo temporal
        wav.write(tmp_path, sample_rate, audio)

        # Transcribir con Whisper
        logger.info(f"Transcribiendo con modelo {modelo_whisper}...")
        whisper_model = WhisperModel(
            modelo_whisper,
            device=config["whisper"]["device"],
            compute_type=config["whisper"]["compute_type"]
        )

        segmentos, _ = whisper_model.transcribe(
            tmp_path,
            language=idioma,
            beam_size=2,
            vad_filter=True,
            hotwords="música volumen youtube abrir cerrar poner siguiente anterior pausa silenciar fecha hora"
        )
        texto = " ".join(s.text for s in segmentos)

        logger.info(f"Transcripción: {texto}")
        return texto.strip().lower()

    finally:
        # Limpiar archivo temporal
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

__all__ = [
    "transcribir"
]
