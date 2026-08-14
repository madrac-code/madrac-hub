"""Tests for Ollama tool calling integration."""
import sys
from pathlib import Path

import pytest

from madrac.mcp.tool_schemas import MADRAC_TOOL_SCHEMAS, _tool_call_to_action

_ASISTENTE_SRC = Path(__file__).resolve().parents[2] / "madrac_asistente"
sys.path.insert(0, str(_ASISTENTE_SRC))

from core import ia  # noqa: E402


def _fake_ollama(chat_fn):
    """Crea un módulo ollama falso en sys.modules (import ollama es local)."""
    mod = type(sys)("ollama")
    mod.chat = chat_fn
    return mod


class TestToolSchemas:
    def test_all_schemas_have_required_fields(self):
        for schema in MADRAC_TOOL_SCHEMAS:
            assert schema["type"] == "function"
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]

    def test_schema_count_matches_server(self):
        assert len(MADRAC_TOOL_SCHEMAS) == 25

    def test_schema_names_match_server_tools(self):
        from madrac.mcp.server import create_server

        mcp = create_server({})
        tool_names = sorted(mcp._tool_manager._tools.keys())
        schema_names = sorted(s["function"]["name"] for s in MADRAC_TOOL_SCHEMAS)
        assert schema_names == tool_names

    def test_transcribe_file_requires_ruta(self):
        schema = next(
            s for s in MADRAC_TOOL_SCHEMAS
            if s["function"]["name"] == "transcribe_file"
        )
        assert "ruta" in schema["function"]["parameters"]["required"]

    def test_execute_assistant_action_requires_accion(self):
        schema = next(
            s for s in MADRAC_TOOL_SCHEMAS
            if s["function"]["name"] == "execute_assistant_action"
        )
        assert "accion" in schema["function"]["parameters"]["required"]


class TestToolCallToAction:
    def test_get_queue_status_maps_correctly(self):
        accion, param = _tool_call_to_action("get_queue_status", {})
        assert accion == "obtener_estado_cola"

    def test_pause_resume_map_correctly(self):
        accion, param = _tool_call_to_action("pause_processing", {})
        assert accion == "pausar_procesamiento"
        accion, param = _tool_call_to_action("resume_processing", {})
        assert accion == "reanudar_procesamiento"

    def test_execute_assistant_action_passes_through(self):
        accion, param = _tool_call_to_action(
            "execute_assistant_action",
            {"accion": "obtener_hora", "parametro": ""}
        )
        assert accion == "obtener_hora"
        assert param == ""

    def test_execute_assistant_action_defaults_to_conversar(self):
        accion, param = _tool_call_to_action("execute_assistant_action", {})
        assert accion == "conversar"

    def test_transcribe_file_passes_ruta(self):
        accion, param = _tool_call_to_action(
            "transcribe_file",
            {"ruta": "/videos/test.mp4", "idioma": "es"}
        )
        assert accion == "transcribir_archivo"
        assert param == "/videos/test.mp4"

    def test_translate_subtitles_joins_srt_and_lang(self):
        accion, param = _tool_call_to_action(
            "translate_subtitles",
            {"archivo_srt": "/subs/a.srt", "idioma_destino": "en"}
        )
        assert accion == "traducir_subtitulos"
        assert param == "/subs/a.srt|en"

    def test_start_dubbing_passes_video_path(self):
        accion, param = _tool_call_to_action(
            "start_dubbing",
            {"video_path": "/videos/peli.mp4", "idioma": "es"}
        )
        assert accion == "iniciar_doblaje"
        assert param == "/videos/peli.mp4"

    def test_read_config_passes_clave(self):
        accion, param = _tool_call_to_action(
            "read_config",
            {"clave": "whisper.modelo"}
        )
        assert accion == "leer_config"
        assert param == "whisper.modelo"

    def test_get_dubbing_status_passes_job_id(self):
        accion, param = _tool_call_to_action(
            "get_dubbing_status",
            {"job_id": "job-123"}
        )
        assert accion == "estado_doblaje"
        assert param == "job-123"

    def test_unknown_tool_falls_back_to_conversar(self):
        accion, param = _tool_call_to_action("unknown_tool", {})
        assert accion == "conversar"
        assert param == ""


class TestConsultarOllamaToolCalling:
    """Tests the tool-calling path in madrac_asistente.core.ia."""

    def test_tool_call_maps_to_action(self, monkeypatch):
        mock_resp = {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "execute_assistant_action",
                            "arguments": {"accion": "obtener_hora", "parametro": ""},
                        }
                    }
                ],
            }
        }

        def fake_chat(model, messages, tools=None):
            assert tools == MADRAC_TOOL_SCHEMAS
            return mock_resp

        monkeypatch.setitem(sys.modules, "ollama", _fake_ollama(fake_chat))

        config = {
            "modelo_ia": {
                "tipo": "ollama",
                "opciones": {"ollama": {"modelo": "llama3"}},
            }
        }
        monkeypatch.setattr(ia, "cargar_config", lambda: config)

        from core.historial import HistorialConversacion

        h = HistorialConversacion()
        h.agregar_usuario("qué hora es")
        accion, parametro = ia._consultar_ollama("qué hora es", h)
        assert accion == "obtener_hora"
        assert parametro == ""

    def test_no_tool_call_parses_json(self, monkeypatch):
        mock_resp = {
            "message": {
                "content": '{"accion": "conversar", "parametro": "Son las 3."}',
                "tool_calls": [],
            }
        }

        def fake_chat(model, messages, tools=None):
            return mock_resp

        monkeypatch.setitem(sys.modules, "ollama", _fake_ollama(fake_chat))

        config = {
            "modelo_ia": {
                "tipo": "ollama",
                "opciones": {"ollama": {"modelo": "llama3"}},
            }
        }
        monkeypatch.setattr(ia, "cargar_config", lambda: config)

        from core.historial import HistorialConversacion

        h = HistorialConversacion()
        h.agregar_usuario("hola")
        accion, parametro = ia._consultar_ollama("hola", h)
        assert accion == "conversar"
        assert parametro == "Son las 3."

    def test_tool_calling_exception_falls_back_to_json(self, monkeypatch):
        calls = {"n": 0}

        def fake_chat(model, messages, tools=None):
            calls["n"] += 1
            if tools:
                raise RuntimeError("model does not support tools")
            return {
                "message": {"content": '{"accion": "abrir_app", "parametro": "chrome"}'}
            }

        monkeypatch.setitem(sys.modules, "ollama", _fake_ollama(fake_chat))

        config = {
            "modelo_ia": {
                "tipo": "ollama",
                "opciones": {"ollama": {"modelo": "llama3"}},
            }
        }
        monkeypatch.setattr(ia, "cargar_config", lambda: config)

        from core.historial import HistorialConversacion

        h = HistorialConversacion()
        h.agregar_usuario("abrí chrome")
        accion, parametro = ia._consultar_ollama("abrí chrome", h)
        assert calls["n"] == 2
        assert accion == "abrir_app"
        assert parametro == "chrome"

    def test_import_error_falls_back_to_json(self, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "madrac.mcp.tool_schemas":
                raise ImportError("no madrac")
            return real_import(name, *args, **kwargs)

        def fake_chat(model, messages, tools=None):
            assert tools is None
            return {
                "message": {"content": '{"accion": "obtener_hora", "parametro": ""}'}
            }

        monkeypatch.setattr(builtins, "__import__", fake_import)
        monkeypatch.setitem(sys.modules, "ollama", _fake_ollama(fake_chat))

        config = {
            "modelo_ia": {
                "tipo": "ollama",
                "opciones": {"ollama": {"modelo": "llama3"}},
            }
        }
        monkeypatch.setattr(ia, "cargar_config", lambda: config)

        from core.historial import HistorialConversacion

        h = HistorialConversacion()
        h.agregar_usuario("qué hora es")
        accion, parametro = ia._consultar_ollama("qué hora es", h)
        assert accion == "obtener_hora"
        assert parametro == ""
