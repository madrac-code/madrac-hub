import json
import os
import sys
import logging
from datetime import datetime
from typing import Dict

from .utils import obtener_ruta_recurso, obtener_ruta_escritura

logger = logging.getLogger(__name__)

_ASIS_TO_SHARED = {
    ("whisper", "device"): "whisper.dispositivo",
    ("whisper", "modelo"): "whisper.modelo",
    ("whisper", "compute_type"): "whisper.compute_type",
    ("interfaz", "tema"): "gui.tema",
    ("audio", "idioma"): "idioma",
}

_ASIS_ONLY_KEYS = {"wakeword", "tts", "modelo_ia", "carpetas", "comentario", "setup_completado"}


def _get_shared_val(key: str):
    try:
        from madrac.config import get_config
        return get_config(key)
    except (ImportError, Exception):
        return None


def _set_shared_val(key: str, value):
    try:
        from madrac.config import set_config
        set_config(key, value)
    except (ImportError, Exception):
        pass


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Merge overlay into base (shallow for top-level, full for section keys)."""
    result = dict(base)
    for k, v in overlay.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k].update(v)
        else:
            result[k] = v
    return result


def cargar_config() -> Dict:
    # 1. Start with the assistant's own bundled defaults
    ruta_base = obtener_ruta_recurso("madrac_asistente/config.json")
    if not os.path.exists(ruta_base):
        ruta_base = obtener_ruta_recurso("config.json")
    if os.path.exists(ruta_base):
        with open(ruta_base, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = {}

    # 2. Overlay shared config values (from madrac.config)
    for (section, key), shared_key in _ASIS_TO_SHARED.items():
        val = _get_shared_val(shared_key)
        if val is not None:
            cfg.setdefault(section, {})[key] = val

    # 3. Overlay local writable config (persisted user overrides)
    ruta_local = obtener_ruta_escritura("config.json")
    if os.path.exists(ruta_local):
        with open(ruta_local, "r", encoding="utf-8") as f:
            local = json.load(f)
        cfg = _deep_merge(cfg, local)

    return cfg


def cargar_perfil() -> Dict:
    ruta = obtener_ruta_escritura("perfiles/default.json")
    if not os.path.exists(ruta):
        ruta = obtener_ruta_recurso("madrac_asistente/perfiles/default.json")
    if not os.path.exists(ruta):
        ruta = obtener_ruta_recurso("perfiles/default.json")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_config(config: Dict):
    for (section, key), shared_key in _ASIS_TO_SHARED.items():
        if section in config and key in config[section]:
            _set_shared_val(shared_key, config[section][key])
    ruta = obtener_ruta_escritura("config.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def guardar_perfil(perfil: Dict):
    ruta = obtener_ruta_escritura("perfiles/default.json")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(perfil, f, indent=2, ensure_ascii=False)


def configurar_logging():
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
