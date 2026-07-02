# ────────────────────────────────────────────────────────────────────
# Audio
# ────────────────────────────────────────────────────────────────────
# Funciones para grabación de audio y detección de wakeword.
# ────────────────────────────────────────────────────────────────────

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


def esperar_wakeword() -> bool:
    """
    Espera a que el usuario diga la palabra clave.

    Returns:
        bool: True si se detectó la palabra clave
    """
    import sounddevice as sd
    import numpy as np
    from openwakeword.model import Model as WakeModel

    config = cargar_config()
    sample_rate = config["audio"]["sample_rate"]
    chunk_size = config["audio"]["chunk_size"]
    device = config["audio"]["dispositivo_mic"]
    modelo_path = config["wakeword"]["modelo"]
    umbral = config["wakeword"]["umbral"]

    logger.info("Esperando palabra clave...")

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
        blocksize=chunk_size
    ) as stream:
        while True:
            chunk, _ = stream.read(chunk_size)
            chunk_np = np.squeeze(chunk)
            prediccion = wake_model.predict(chunk_np)
            score = list(prediccion.values())[0]

            if score >= umbral:
                logger.info(f"Palabra clave detectada (score: {score:.2f})")
                return True

__all__ = [
    "grabar_audio",
    "esperar_wakeword"
]
