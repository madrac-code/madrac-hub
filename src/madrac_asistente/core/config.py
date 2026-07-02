# ────────────────────────────────────────────────────────────────────
# Configuración
# ────────────────────────────────────────────────────────────────────
# Funciones para cargar y guardar configuración y perfiles del usuario.
# ────────────────────────────────────────────────────────────────────

import json
import os
import sys
import logging
from datetime import datetime
from typing import Dict

from .utils import obtener_ruta_recurso, obtener_ruta_escritura

# Configurar logging
logger = logging.getLogger(__name__)


def cargar_config() -> Dict:
    """Carga config.json: primero junto al .exe (modificaciones), sino bundle."""
    ruta = obtener_ruta_escritura("config.json")
    if not os.path.exists(ruta):
        ruta = obtener_ruta_recurso("config.json")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_perfil() -> Dict:
    """Carga perfil: primero junto al .exe (modificaciones), sino bundle."""
    ruta = obtener_ruta_escritura("perfiles/default.json")
    if not os.path.exists(ruta):
        ruta = obtener_ruta_recurso("perfiles/default.json")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_config(config: Dict):
    """Guarda config.json junto al ejecutable."""
    ruta = obtener_ruta_escritura("config.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def guardar_perfil(perfil: Dict):
    """Guarda el perfil del usuario junto al ejecutable."""
    ruta = obtener_ruta_escritura("perfiles/default.json")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(perfil, f, indent=2, ensure_ascii=False)


def configurar_logging():
    """Configura el sistema de logging del asistente (usa shared si disponible)."""
    try:
        from madrac.core.logging import setup_logging, get_logger
        setup_logging()
        return get_logger("asistente")
    except ImportError:
        ruta_logs = obtener_ruta_escritura("logs")
        os.makedirs(ruta_logs, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(ruta_logs, f"jarvis_{timestamp}.log")),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

__all__ = [
    "cargar_config",
    "cargar_perfil",
    "guardar_config",
    "guardar_perfil",
    "configurar_logging",
    "logger"
]
