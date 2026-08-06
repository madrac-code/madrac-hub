# ────────────────────────────────────────────────────────────────────
# Audio
# ────────────────────────────────────────────────────────────────────
# Funciones para grabación de audio y detección de wakeword.
# ────────────────────────────────────────────────────────────────────

from pathlib import Path
from typing import Tuple

from .config import cargar_config, logger


def grabar_audio(segundos: int = 5):
    """
    Graba audio del micrófono seleccionado.

    Args:
        segundos (int): duración de la grabación

    Returns:
        np.ndarray: audio grabado
    """
    import sounddevice as sd
    import numpy as np
    config = cargar_config()
    sample_rate = config["audio"]["sample_rate"]
    device = config["audio"]["dispositivo_mic"]

    logger.info(f"Grabando {segundos} segundos desde dispositivo {device}...")

    audio = sd.rec(
        int(segundos * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        device=device
    )
    sd.wait()

    return audio


def _modelos_wakeword_dir() -> Path:
    """Return the directory where openwakeword keeps its bundled models.

    Uses the installed openwakeword package location so feature models
    (melspectrogram, embedding) and wakeword models are co-located.
    """
    import openwakeword
    return Path(openwakeword.__file__).resolve().parent / "resources" / "models"


def _asegurar_modelo_wakeword() -> str:
    """Ensure the wakeword model file exists, downloading it if missing.

    Downloads ``hey_jarvis_v0.1.onnx`` (and the feature models) into
    the openwakeword ``resources/models`` directory using the package's
    built-in downloader.

    Returns:
        Absolute path to the wakeword model file.

    Raises:
        RuntimeError: if the model cannot be located or downloaded.
    """
    config = cargar_config()
    modelo = config.get("wakeword", {}).get("modelo", "hey_jarvis_v0.1.onnx")
    modelos_dir = _modelos_wakeword_dir()
    modelo_path = modelos_dir / modelo

    if modelo_path.exists():
        logger.info(f"Wakeword model found: {modelo_path}")
        return str(modelo_path)

    logger.info(f"Wakeword model missing — descargando {modelo} ...")
    from openwakeword.utils import download_models

    modelos_dir.mkdir(parents=True, exist_ok=True)
    try:
        download_models(
            model_names=["hey_jarvis"],
            target_directory=str(modelos_dir),
        )
    except Exception as e:
        logger.error(f"Error descargando wakeword model: {e}")
        raise RuntimeError(
            f"No se pudo descargar el modelo de wakeword ({modelo}). "
            "Revisá tu conexión a internet e intentá de nuevo."
        ) from e

    if not modelo_path.exists():
        raise RuntimeError(
            f"El modelo de wakeword ({modelo}) no se descargó correctamente "
            f"hacia {modelo_path}. Revisá tu conexión e intentá de nuevo."
        )
    logger.info(f"Wakeword model descargado: {modelo_path}")
    return str(modelo_path)


def esperar_wakeword(stop_event=None) -> bool:
    """
    Espera a que el usuario diga la palabra clave.

    Args:
        stop_event: threading.Event opcional para interrumpir la escucha

    Returns:
        bool: True si se detectó la palabra clave, False si se detuvo
    """
    import sounddevice as sd
    import numpy as np
    from openwakeword.model import Model as WakeModel

    config = cargar_config()
    sample_rate = config.get("audio", {}).get("sample_rate", 16000)
    chunk_size = config.get("audio", {}).get("chunk_size", 1280)
    device = config.get("audio", {}).get("dispositivo_mic")
    palabra = config.get("wakeword", {}).get("palabra", "madrac")
    umbral = config.get("wakeword", {}).get("umbral", 0.5)
    framework = config.get("wakeword", {}).get("framework", "onnx")
    modelo_path = _asegurar_modelo_wakeword()

    logger.info(f"Esperando palabra clave '{palabra}'...")

    wake_model = WakeModel(
        wakeword_models=[modelo_path],
        inference_framework=framework
    )
    wake_model.reset()

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        device=device,
        blocksize=chunk_size
    ) as stream:
        while True:
            if stop_event and stop_event.is_set():
                return False
            chunk, _ = stream.read(chunk_size)
            chunk_np = np.squeeze(chunk)
            prediccion = wake_model.predict(chunk_np)
            score = list(prediccion.values())[0]

            if score >= umbral:
                logger.info(f"Palabra clave detectada (score: {score:.2f})")
                return True

__all__ = [
    "grabar_audio",
    "esperar_wakeword",
    "_asegurar_modelo_wakeword"
]
