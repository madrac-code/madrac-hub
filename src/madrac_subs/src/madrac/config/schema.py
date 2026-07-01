"""Config schema validation and migration for MADRAC-SUBS v3."""

import logging
from typing import Any, Dict, List, Optional, Tuple, Type

from .defaults import DEFAULTS, CONFIG_VERSION

logger = logging.getLogger("madrac.config.schema")

# Type schema: maps dotted keys to expected Python types
_TYPE_SCHEMA: Dict[str, Tuple[Type, ...]] = {
    "version": (int,),
    "whisper.modelo": (str,),
    "whisper.task": (str,),
    "whisper.detectar_idioma": (bool,),
    "whisper.dispositivo": (str,),
    "whisper.compute_type": (str,),
    "whisper.beam_size": (int,),
    "whisper.best_of": (int,),
    "whisper.temperature": (float, int),
    "whisper.vad_filter": (bool,),
    "whisper.condition_on_previous_text": (bool,),
    "whisper.word_timestamps": (bool,),
    "whisper.thread_count": (int,),
    "traduccion.habilitada": (bool,),
    "traduccion.motor": (str,),
    "traduccion.idioma_destino": (str,),
    "traduccion.cache_modelos": (bool,),
    "traduccion.motor_por_idioma": (dict,),
    "motores_traduccion.gemini.api_key": (str,),
    "motores_traduccion.gemini.modelo": (str,),
    "motores_traduccion.libretranslate.url": (str,),
    "motores_traduccion.libretranslate.api_key": (str,),
    "motores_traduccion.libretranslate.timeout": (int,),
    "motores_traduccion.google.timeout": (int,),
    "subtitulos.max_chars_por_linea": (int,),
    "subtitulos.max_lineas_por_subtitulo": (int,),
    "subtitulos.duracion_minima_ms": (int,),
    "subtitulos.duracion_maxima_ms": (int,),
    "subtitulos.dividir_en_pausas_naturales": (bool,),
    "procesamiento.procesamiento_paralelo": (bool,),
    "procesamiento.max_workers": (int,),
    "procesamiento.reintentos_fallidos": (int,),
    "procesamiento.limpiar_cache_temporal": (bool,),
    "procesamiento.preferir_subtitulos_embebidos": (bool,),
    "procesamiento.generar_txt": (bool,),
    "gpu.advertencia_thermal": (bool,),
    "gpu.max_utilization_percent": (int,),
    "gpu.monitoreo_activo": (bool,),
    "gpu.prefer_gpu": (bool,),
    "comunidad.habilitado": (bool,),
    "comunidad.auto_buscar": (bool,),
    "comunidad.auto_descargar": (bool,),
    "comunidad.auto_compartir": (bool,),
    "comunidad.share_consent_given": (bool,),
    "comunidad.subir_automaticamente": (bool,),
    "comunidad.online": (bool,),
    "comunidad.normalizacion_habilitada": (bool,),
    "salida.formato": (str,),
    "salida.directorio": (str,),
    "file_handlers.registered": (bool,),
    "idioma": (str,),
}

_ENUMS = {
    "whisper.modelo": {"tiny", "base", "small", "medium", "large-v3"},
    "whisper.dispositivo": {"cpu", "cuda", "auto"},
    "whisper.compute_type": {"int8", "int8_float16", "float16", "float32"},
    "whisper.task": {"transcribe", "translate"},
    "traduccion.motor": {"marianmt", "gemini", "libretranslate", "google"},
    "traduccion.idioma_destino": {"es", "en", "fr", "de", "it", "pt"},
    "motores_traduccion.gemini.modelo": {"gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro", "gemini-3.5-flash"},
}


def _set_at_path(root: Dict, dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    for p in parts[:-1]:
        root = root.setdefault(p, {})
    root[parts[-1]] = value


def _get_at_path(root: Dict, dotted: str) -> Any:
    parts = dotted.split(".")
    for p in parts:
        if isinstance(root, dict):
            root = root.get(p)
        else:
            return None
    return root


def validate_config(cfg: Dict[str, Any]) -> List[str]:
    """Validate config against type schema and enum constraints.

    Returns a list of warning/error messages. Empty list = valid.
    """
    warnings: List[str] = []

    # Check version
    ver = cfg.get("version", 0)
    if ver != CONFIG_VERSION:
        warnings.append(f"Config version {ver}, expected {CONFIG_VERSION}")

    # Type-check known keys
    for dotted, expected_types in _TYPE_SCHEMA.items():
        val = _get_at_path(cfg, dotted)
        if val is not None and not isinstance(val, expected_types):
            warnings.append(
                f"{dotted}: expected {expected_types}, got {type(val).__name__} ({val})"
            )

    # Enum checks
    for dotted, valid_values in _ENUMS.items():
        val = _get_at_path(cfg, dotted)
        if val is not None and val not in valid_values:
            warnings.append(
                f"{dotted}: '{val}' not in {sorted(valid_values)}"
            )

    return warnings


def merge_with_defaults(user_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Merge user config over the top of defaults, recursively."""
    from copy import deepcopy

    merged = deepcopy(DEFAULTS)

    def _merge(target: Dict, source: Dict) -> None:
        for k, v in source.items():
            if k in target and isinstance(target[k], dict) and isinstance(v, dict):
                _merge(target[k], v)
            else:
                target[k] = v

    _merge(merged, user_cfg)
    # Always set version
    merged["version"] = CONFIG_VERSION
    return merged


def migrate_v2_to_v3(v2_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate a v2 JSON config to v3 format.

    Handles:
    - Key renames (V2_TO_V3_KEY_MAP)
    - Missing keys -> defaults
    - Version bump
    """
    from .defaults import V2_TO_V3_KEY_MAP

    v3_cfg = {}
    for old_key, new_key in V2_TO_V3_KEY_MAP.items():
        val = _get_at_path(v2_cfg, old_key)
        if val is not None:
            _set_at_path(v3_cfg, new_key, val)

    # Copy full sections that haven't changed
    for section in [
        "whisper", "traduccion", "motores_traduccion", "subtitulos",
        "gui", "procesamiento", "directorios", "gpu",
    ]:
        if section in v2_cfg and isinstance(v2_cfg[section], dict):
            v3_cfg.setdefault(section, {}).update(
                {k: v for k, v in v2_cfg[section].items()
                 if k not in v3_cfg.get(section, {})}
            )

    # Merge over defaults
    result = merge_with_defaults(v3_cfg)

    logger.info("Migrated config v2 -> v3 (%d keys mapped)", len(V2_TO_V3_KEY_MAP))
    return result
