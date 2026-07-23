# Phase 3 — MCP Server Integration

**Status**: IN PROGRESS
**Started**: 2026-07-23
**Prerequisite**: Phase 2 complete ✅

## Goal

Expose MADRAC capabilities as MCP tools so that:
1. The internal Ollama LLM uses structured tools instead of fragile JSON prompts
2. External agents (Claude Desktop, Cursor, autonomous scripts) can control MADRAC without UI interaction
3. madrac-recon (future) slots in as additional MCP tools without architectural changes

## Architecture Decision

Option A (Full MCP Server) chosen per ADR-008.

FastMCP server running as subprocess of MADRAC-SUBS, communicating via stdio transport initially, Streamable HTTP in Phase 3B.

## Implementation Plan

### Phase 3A — Core MCP Server (this sprint)

**New file**: src/madrac_subs/src/madrac/mcp/server.py

Tools to implement (in priority order):

| Tool | Input | Output | Priority |
|------|-------|--------|----------|
| get_queue_status | — | dict | P0 |
| transcribe_file | ruta: str, idioma: str | str | P0 |
| translate_subtitles | archivo_srt: str, idioma_destino: str | str | P0 |
| pause_processing | — | bool | P1 |
| execute_assistant_action | accion: str, parametro: str | str | P1 |
| read_config | clave: str | dict | P1 |
| get_dubbing_status | job_id: str | dict | P2 |
| start_dubbing | video_path: str, idioma: str | str | P2 |

Resources to implement:

| Resource | URI | Content |
|----------|-----|---------|
| Queue state | queue://estado | {pendientes, en_progreso, completados} |
| Job progress | queue://progreso/{id} | {id, progreso, etapa} |
| Recent logs | log://ultimos/{n} | [last n log entries] |
| Current config | config://actual | full config dict |

**Integration point**: AssistantManager gains start_mcp_server() method that launches the FastMCP subprocess and holds a reference.

### Phase 3B — Ollama Tool Calling (after 3A validated)

Update the Ollama prompt in core/ia.py to use MCP tool schemas instead of the current fragile JSON format.

Before (current):
```
Responde SOLO con JSON: {"accion": "...", "parametro": "..."}
```

After (Phase 3B):
```
You have access to these tools: [tool schemas from MCP]
Call them when the user requests a MADRAC action.
```

### Phase 3C — External Access (after 3B validated)

Add Streamable HTTP transport to the MCP server so external agents can connect without being a subprocess of SUBS.

Port: 7654 (configurable)
Auth: local token (no internet exposure initially)

## madrac-recon Integration Path

When madrac-recon is implemented, its capabilities register as additional MCP tools on the same server:

```python
@mcp.tool()
async def clone_user_voice(audio_samples_dir: str) -> str:
    """Train a TTS voice model from user audio samples (~30 min clean audio).
    Returns path to trained model."""
    # Coqui TTS or StyleTTS2 training
    ...

@mcp.tool()
async def train_wakeword(keyword: str, samples_dir: str) -> str:
    """Train a custom wakeword model from user voice samples.
    Returns path to trained openWakeWord model."""
    ...

@mcp.tool()
async def transcribe_realtime(duration_seconds: int) -> str:
    """Transcribe audio from microphone in real time using
    faster-whisper streaming mode."""
    ...
```

madrac-recon itself is a separate component (D:\madrac-recon, future repo) that exposes its capabilities via this shared MCP server.

## Dependencies

New dependency: mcp SDK
```
pip install mcp
Pure Python, lightweight, no C extensions
Add to requirements.txt in madrac-subs and dev-requirements.txt
```

## Acceptance Criteria for Phase 3A

- [ ] FastMCP server starts as subprocess of MADRAC-SUBS
- [ ] get_queue_status tool returns real queue data
- [ ] transcribe_file tool triggers real Whisper transcription
- [ ] translate_subtitles tool triggers real MarianMT/Gemini translation
- [ ] MCP server accessible from Claude Desktop (local stdio connection)
- [ ] No regression in existing 290 + 13 + 14 tests
- [ ] New tests: test_mcp_server.py with at least 10 tool call tests

## Files to Create in Phase 3A

```
src/madrac_subs/src/madrac/mcp/
    __init__.py
    server.py          ← FastMCP server + tool definitions
    tools/
        __init__.py
        queue.py       ← get_queue_status, pause_processing
        transcription.py ← transcribe_file
        translation.py ← translate_subtitles
        assistant.py   ← execute_assistant_action
        config.py      ← read_config
        dubbing.py     ← get_dubbing_status, start_dubbing
    resources/
        __init__.py
        queue.py       ← queue:// resources
        logs.py        ← log:// resources
        config.py      ← config:// resources

src/madrac_subs/tests/
    test_mcp_server.py ← 10+ tool call tests
```

## Known Constraints

- MCP server must not block the Qt event loop
- stdio transport: MCP server is a subprocess, not a thread
- FastMCP handles JSON-RPC framing automatically
- All tools must be async (FastMCP requirement)
- Tool errors must return structured error responses, not raise
