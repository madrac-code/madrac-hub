"""
Ollama-compatible tool schemas for MADRAC MCP tools.
Used by core/ia.py for structured tool calling.
Kept in sync with mcp/server.py tool definitions.
"""

from typing import Any, Tuple

MADRAC_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_queue_status",
            "description": "Get the current state of the processing queue. "
                           "Returns counts of pending, active, and completed jobs.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pause_processing",
            "description": "Pause the subtitle processing queue.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resume_processing",
            "description": "Resume the subtitle processing queue after pausing.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transcribe_file",
            "description": "Transcribe an audio or video file using Whisper. "
                           "Adds the file to the processing queue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ruta": {
                        "type": "string",
                        "description": "Absolute path to the audio or video file"
                    },
                    "idioma": {
                        "type": "string",
                        "description": "Language code: 'es', 'en', 'fr', 'pt', etc.",
                        "default": "es"
                    }
                },
                "required": ["ruta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "translate_subtitles",
            "description": "Translate a .srt subtitle file to another language.",
            "parameters": {
                "type": "object",
                "properties": {
                    "archivo_srt": {
                        "type": "string",
                        "description": "Absolute path to the source .srt file"
                    },
                    "idioma_destino": {
                        "type": "string",
                        "description": "Target language code: 'en', 'fr', 'pt', 'de', 'it'"
                    }
                },
                "required": ["archivo_srt", "idioma_destino"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_assistant_action",
            "description": "Execute a named assistant action. Available actions: "
                           "reproducir_musica, detener_musica, abrir_app, "
                           "cerrar_ventana, obtener_hora, obtener_fecha, "
                           "escribir, youtube, play_pause, siguiente_cancion, "
                           "anterior_cancion, cerrar_pestania, subir_volumen, "
                           "bajar_volumen, silenciar, establecer_volumen, conversar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {
                        "type": "string",
                        "description": "Action name to execute"
                    },
                    "parametro": {
                        "type": "string",
                        "description": "Optional parameter for the action",
                        "default": ""
                    }
                },
                "required": ["accion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_config",
            "description": "Read the current MADRAC configuration. "
                           "Use dot notation for specific keys, e.g. 'whisper.modelo'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "clave": {
                        "type": "string",
                        "description": "Dot-notation config key, or empty for full config",
                        "default": ""
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_dubbing_status",
            "description": "Get the status of a dubbing job.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Job ID from start_dubbing. Empty for all jobs.",
                        "default": ""
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_dubbing",
            "description": "Start a dubbing job for a video file using Edge TTS.",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_path": {
                        "type": "string",
                        "description": "Absolute path to the video file"
                    },
                    "idioma": {
                        "type": "string",
                        "description": "Target language for dubbing",
                        "default": "es"
                    }
                },
                "required": ["video_path"]
            }
        }
    }
]


def _tool_call_to_action(
    tool_name: str, args: dict[str, Any]
) -> tuple[str, str]:
    """Map MCP tool name + args to (accion, parametro) for the action executor."""
    mapping = {
        "get_queue_status": ("obtener_estado_cola", ""),
        "pause_processing": ("pausar_procesamiento", ""),
        "resume_processing": ("reanudar_procesamiento", ""),
        "execute_assistant_action": (
            args.get("accion", "conversar"),
            args.get("parametro", "")
        ),
        "read_config": ("leer_config", args.get("clave", "")),
        "get_dubbing_status": ("estado_doblaje", args.get("job_id", "")),
    }

    if tool_name in mapping:
        return mapping[tool_name]

    # Tools that take file paths — pass path as parametro
    if tool_name == "transcribe_file":
        return "transcribir_archivo", args.get("ruta", "")
    if tool_name == "translate_subtitles":
        dest = args.get("idioma_destino", "en")
        srt = args.get("archivo_srt", "")
        return "traducir_subtitulos", f"{srt}|{dest}"
    if tool_name == "start_dubbing":
        return "iniciar_doblaje", args.get("video_path", "")

    # Unknown tool — treat as conversation
    return "conversar", ""