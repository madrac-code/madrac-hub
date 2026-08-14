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

# Workspace tools (6 tools)
MADRAC_TOOL_SCHEMAS.extend([
    {
        "type": "function",
        "function": {
            "name": "get_workspace_info",
            "description": "Get metadata and artifact status for a job workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Job ID (sha256-<hash>)"
                    }
                },
                "required": ["job_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_workspaces",
            "description": "List all available job workspaces with artifact status.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_segments",
            "description": "Get all transcription segments for a job. Returns list of {id, start, end, text}.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Job ID (sha256-<hash>)"
                    }
                },
                "required": ["job_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rename_speaker",
            "description": "Rename a speaker track in a workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "speaker_id": {"type": "integer"},
                    "name": {"type": "string"}
                },
                "required": ["job_id", "speaker_id", "name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_subtitle_segment",
            "description": "Edit the text of a specific subtitle segment. Use get_segments first to find the segment_id. Changes are saved immediately to the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Job ID (sha256-<hash>)"
                    },
                    "segment_id": {
                        "type": "integer",
                        "description": "Segment index (0-based)"
                    },
                    "new_text": {
                        "type": "string",
                        "description": "New text for this segment"
                    }
                },
                "required": ["job_id", "segment_id", "new_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "export_srt",
            "description": "Export edited segments from workspace as a .srt file. Use after editing segments with edit_subtitle_segment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Job ID (sha256-<hash>)"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional output path. If empty, saves next to source video.",
                        "default": ""
                    }
                },
                "required": ["job_id"]
            }
        }
    }
])

# MUI window tools (5 tools)
MADRAC_TOOL_SCHEMAS.extend([
    {
        "type": "function",
        "function": {
            "name": "create_window",
            "description": "Create a new MUI window with procedural widgets. "
                           "Widget types: label, button, table, "
                           "segment_selector, audio_player, waveform. "
                           "Button actions: {\"tool\": name, \"params\": {...}} "
                           "or {\"internal\": play_segment|record_segment|close_window}.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Window title"
                    },
                    "widgets": {
                        "type": "array",
                        "description": "List of widget descriptors",
                        "items": {"type": "object"}
                    },
                    "job_id": {
                        "type": "string",
                        "description": "Optional workspace job ID for persistence",
                        "default": ""
                    },
                    "keybindings": {
                        "type": "object",
                        "description": "Optional dict of key -> action (reserved)",
                        "default": {}
                    }
                },
                "required": ["title", "widgets"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_widget",
            "description": "Update widget properties in a live MUI window. "
                           "Supported props: text, enabled.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_id": {
                        "type": "string",
                        "description": "Window ID from create_window"
                    },
                    "widget_id": {
                        "type": "string",
                        "description": "Widget ID from the window's descriptors"
                    },
                    "props": {
                        "type": "object",
                        "description": "Props to update, e.g. {\"text\": \"...\"}"
                    }
                },
                "required": ["window_id", "widget_id", "props"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "close_window",
            "description": "Close an MUI window by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_id": {
                        "type": "string",
                        "description": "Window ID from create_window"
                    }
                },
                "required": ["window_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_windows",
            "description": "List open MUI windows with their status.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_window_events",
            "description": "Get pending user-interaction events for an MUI window. "
                           "Reading drains the queue (events are consumed).",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_id": {
                        "type": "string",
                        "description": "Window ID from create_window"
                    }
                },
                "required": ["window_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "diarize_speakers",
            "description": "Diarize speakers for a workspace job and persist "
                           "them (stems/speakers/speaker_N.wav + speakers.json).",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Workspace job ID (sha256-<hex>). "
                                       "Mutually exclusive with video_path"
                    },
                    "video_path": {
                        "type": "string",
                        "description": "Absolute path to the source video "
                                       "(computes the job ID)"
                    },
                    "min_speakers": {
                        "type": "integer",
                        "description": "Minimum number of speakers to look for",
                        "default": 1
                    },
                    "max_speakers": {
                        "type": "integer",
                        "description": "Maximum number of speakers to look for",
                        "default": 8
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "map_speakers_to_segments",
            "description": "Map diarized speakers to subtitle segments by temporal overlap. "
                           "Produces speaker_segments.json with speaker_id, speaker_name, "
                           "and confidence per segment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Workspace job ID (sha256-<hex>). "
                                       "Must have both segments.json and speakers.json"
                    }
                },
                "required": ["job_id"]
            }
        }
    }
])


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