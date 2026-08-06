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
    motor = config.get("tts", {}).get("motor", "edge")

    logger.info(f"Asistente: {texto}")

    if motor == "edge":
        return _hablar_edge(texto)
    elif motor == "powershell":
        return _hablar_powershell(texto)
    elif motor == "pyttsx3":
        return _hablar_pyttsx3(texto)
    else:
        logger.error(f"Motor TTS desconocido: {motor}")
        return False


def _hablar_edge(texto: str) -> bool:
    """Usa Microsoft Edge neural voices (paquete ``edge-tts``) para hablar.

    Descarga la síntesis y la reproduce por el altavoz predeterminado
    usando ``winsound``. Fallback a PowerShell si falla.
    """
    import asyncio
    import tempfile
    import winsound

    config = cargar_config()
    voz = config.get("tts", {}).get("voz", "es-MX-DaliaNeural")
    velocidad = config.get("tts", {}).get("velocidad", 1.0)

    tmp = None
    try:
        import edge_tts

        async def _sintetizar(path: str):
            comunicador = edge_tts.Communicate(texto, voz, rate=f"{velocidad:+.0f}%")
            await comunicador.save(path)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp = f.name

        asyncio.run(_sintetizar(tmp))
        winsound.PlaySound(tmp, winsound.SND_FILENAME)
        return True
    except ModuleNotFoundError:
        logger.warning("edge_tts no está instalado — usando PowerShell TTS como fallback")
        return _hablar_powershell(texto)
    except Exception as e:
        logger.error(f"Error en TTS edge: {e}")
        try:
            return _hablar_powershell(texto)
        except Exception:
            return False
    finally:
        if tmp:
            try:
                import os
                os.remove(tmp)
            except Exception:
                pass


def _hablar_powershell(texto: str) -> bool:
    """Usa PowerShell y TTS de Windows para hablar."""
    config = cargar_config()
    voz = config.get("tts", {}).get("voz", "")

    # Limpiar caracteres problemáticos
    texto_safe = texto.replace("'", "").replace('"', "")

    try:
        cmd = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"if ('{voz}' -in $s.GetInstalledVoices().VoiceInfo.Name) {{ "
            f"$s.SelectVoice('{voz}') }}; "
            f"$s.Speak('{texto_safe}')"
        )
        r = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if r.returncode != 0:
            logger.error(
                f"Error en TTS PowerShell: {r.stderr.decode('utf-8', errors='replace')}"
            )
            return False
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
