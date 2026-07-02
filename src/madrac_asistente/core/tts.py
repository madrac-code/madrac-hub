# ────────────────────────────────────────────────────────────────────
# TTS
# ────────────────────────────────────────────────────────────────────
# Funciones para síntesis de voz (Text-to-Speech).
# ────────────────────────────────────────────────────────────────────

import subprocess
from typing import Tuple

from .config import cargar_config, logger


def hablar(texto: str) -> bool:
    """
    Convierte texto a voz usando el motor TTS configurado.

    Args:
        texto (str): texto a reproducir

    Returns:
        bool: True si fue exitoso
    """
    config = cargar_config()
    motor = config["tts"]["motor"]

    logger.info(f"Asistente: {texto}")

    if motor == "powershell":
        return _hablar_powershell(texto)
    elif motor == "pyttsx3":
        return _hablar_pyttsx3(texto)
    else:
        logger.error(f"Motor TTS desconocido: {motor}")
        return False


def _hablar_powershell(texto: str) -> bool:
    """Usa PowerShell y TTS de Windows para hablar."""
    config = cargar_config()
    voz = config["tts"]["voz"]

    # Limpiar caracteres problemáticos
    texto_safe = texto.replace("'", "").replace('"', "")

    try:
        subprocess.run([
            "powershell", "-Command",
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.SelectVoice('{voz}'); "
            f"$s.Speak('{texto_safe}')"
        ], capture_output=True, timeout=30)
        return True
    except Exception as e:
        logger.error(f"Error en TTS PowerShell: {e}")
        return False


def _hablar_pyttsx3(texto: str) -> bool:
    """Usa pyttsx3 para hablar."""
    try:
        import pyttsx3
        config = cargar_config()
        voz = config["tts"]["voz"]

        engine = pyttsx3.init()
        # Configurar voz (si está disponible)
        # engine.setProperty('voice', voz)
        engine.say(texto)
        engine.runAndWait()
        return True
    except Exception as e:
        logger.error(f"Error en TTS pyttsx3: {e}")
        return False

__all__ = [
    "hablar",
    "_hablar_powershell",
    "_hablar_pyttsx3"
]
