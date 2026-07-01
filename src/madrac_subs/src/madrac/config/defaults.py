"""
Default configuration values for MADRAC-SUBS v3.
Centralized defaults with version information.
"""

CONFIG_VERSION = 3

DEFAULTS = {
    "version": CONFIG_VERSION,
    "whisper": {
        "modelo": "base",
        "task": "transcribe",
        "detectar_idioma": True,
        "dispositivo": "cpu",
        "compute_type": "int8",
        "beam_size": 5,
        "best_of": 5,
        "temperature": 0.0,
        "vad_filter": True,
        "condition_on_previous_text": True,
        "word_timestamps": True,
        "thread_count": 0,  # 0 = auto-detect
    },
    "traduccion": {
        "habilitada": True,
        "motor": "marianmt",
        "idioma_destino": "es",
        "cache_modelos": True,
    },
    "motores_traduccion": {
        "marianmt": {
            "modelo": "Helsinki-NLP/opus-mt-en-es",
            "modelo_ja_en": "Helsinki-NLP/opus-mt-ja-en",
            "modelo_nl_en": "Helsinki-NLP/opus-mt-nl-en",
            "dispositivo": "cpu",
            "batch_size": 16,
            "half_precision": False,
            "max_length": 128,
            "timeout_lote_s": 120,
        },
    "gemini": {
        "api_key": "",
        "modelo": "gemini-2.5-flash",
    },
        "libretranslate": {
            "url": "http://localhost:5000",
            "api_key": "",
            "timeout": 30,
        },
        "google": {
            "timeout": 30,
        },
    },
    "subtitulos": {
        "max_chars_por_linea": 42,
        "max_lineas_por_subtitulo": 2,
        "duracion_minima_ms": 1500,
        "duracion_maxima_ms": 7000,
        "dividir_en_pausas_naturales": True,
    },
    "gui": {
        "ventana_ancho": 1000,
        "ventana_alto": 800,
        "ventana_x": None,
        "ventana_y": None,
        "tema": "dark",
        "color_tema": "blue",
        "notificaciones_sistema": True,
        "ultimo_directorio": "",
        "splitter_sizes": None,
        "log_collapsed": False,
    },
    "procesamiento": {
        "procesamiento_paralelo": False,
        "max_workers": 1,
        "reintentos_fallidos": 3,
        "limpiar_cache_temporal": True,
        "preferir_subtitulos_embebidos": True,
        "generar_txt": False,
    },
    "directorios": {
        "cache_modelos": "",  # Empty = use HF default
        "temporal": "",  # Empty = use default
        "subcarpeta_salida": "",
    },
    "gpu": {
        "advertencia_thermal": True,
        "max_utilization_percent": 85,
        "monitoreo_activo": True,
        "prefer_gpu": True,  # Auto-detect and use GPU if available
    },
    "comunidad": {
        "habilitado": True,
        "auto_buscar": True,
        "auto_descargar": True,
        "auto_compartir": False,
        "subir_automaticamente": True,
        "share_consent_given": False,
        "online": False,
        "normalizacion_habilitada": True,
    },
    "setup_completed": False,
    "editor": {
        "easy_splitter_sizes": [400, 120],
    },
    "file_handlers": {
        "registered": False,
    },
    "idioma": "es",
    "plugins": {
        "active": [],
        "search_paths": [],
    },
    "mux": {
        "habilitado": False,
    },
    "salida": {
        "formato": "srt",
        "directorio": "",
    },
    "perfilado": {
        "enabled": False,
        "log_interval_s": 10,
    },
}

# Keys that should be migrated from v2 config if present
V2_TO_V3_KEY_MAP = {
    "whisper.model": "whisper.modelo",
    "whisper.device": "whisper.dispositivo",
    "translation.enabled": "traduccion.habilitada",
    "translation.engine": "traduccion.motor",
    "translation.target_lang": "traduccion.idioma_destino",
}