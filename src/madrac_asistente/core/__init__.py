# ────────────────────────────────────────────────────────────────────
# Núcleo del Asistente MADRAC
# ────────────────────────────────────────────────────────────────────
# Módulo central que contiene las utilidades compartidas del asistente.
# Este módulo se divide en sub-módulos especializados para mejor mantenibilidad.
# ────────────────────────────────────────────────────────────────────

from .config import (
    cargar_config,
    cargar_perfil,
    guardar_config,
    guardar_perfil,
    configurar_logging,
    logger
)

from .audio import grabar_audio, esperar_wakeword
from .transcription import transcribir
from .tts import hablar
from .ia import (
    normalizar,
    _distancia_edicion,
    detectar_intencion_basica,
    consultar_ia,
    _consultar_ollama,
    _consultar_claude,
    _consultar_openai
)
from .actions import ejecutar_accion

__all__ = [
    # Configuración
    "cargar_config",
    "cargar_perfil",
    "guardar_config",
    "guardar_perfil",
    "configurar_logging",
    "logger",
    # Audio
    "grabar_audio",
    "esperar_wakeword",
    # Transcripción
    "transcribir",
    # TTS
    "hablar",
    # IA
    "normalizar",
    "_distancia_edicion",
    "detectar_intencion_basica",
    "consultar_ia",
    "_consultar_ollama",
    "_consultar_claude",
    "_consultar_openai",
    # Acciones
    "ejecutar_accion"
]
