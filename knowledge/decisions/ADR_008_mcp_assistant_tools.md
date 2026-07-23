# ADR-008 — MCP Server for Assistant Tools and External Agency

**Date**: 2026-07-23
**Status**: Proposed — awaiting implementation decision
**Deciders**: Human
**Components affected**: ASISTENTE, SUBS, future RECON

## Context

The current assistant architecture has three known limitations:

1. Actions are hardcoded in core/actions.py — adding a new action requires editing code
2. The LLM (Ollama/llama3) receives intent as JSON prompts which are fragile and sometimes produce malformed output
3. No external agency — the assistant cannot be controlled by other systems or AI agents without direct integration

MCP (Model Context Protocol) is an open standard (Anthropic, 2024) that allows AI models to connect to external tools via JSON-RPC. An MCP server in MADRAC-SUBS would expose tools and resources that any MCP-compatible host (Claude Desktop, Cursor, autonomous agents) can call.

An MCP server is already active in the development environment (roblox_studio), confirming infrastructure compatibility.

## Options Considered

| Option | Description | Complexity | Impact |
|--------|-------------|------------|--------|
| A: Full MCP Server | FastMCP server exposing tools + resources | Medium (~400 lines) | High — full external agency |
| B: Improved JSON schema | Strict typed JSON for Ollama prompts only | Low (~50 lines) | Low — internal only |
| C: Minimal HTTP API | Flask endpoints for external control | Low (~100 lines) | Medium — external but not MCP standard |

## Proposed Tools (Option A)

```python
transcribir_archivo(ruta, idioma) -> str
traducir_subtitulos(archivo_srt, idioma_destino) -> str
obtener_estado_cola() -> dict
pausar_procesamiento() -> bool
ejecutar_accion_asistente(accion, parametro) -> str
leer_config(clave) -> dict
```

## Proposed Resources (Option A)

```
queue://estado
queue://progreso/{id}
log://ultimos/{n}
config://actual
```

## Integration Path (if Option A chosen)

- Phase 1: MCP Server created alongside existing ejecutar_accion() — no breaking changes, both run in parallel
- Phase 2: Ollama prompt updated to prefer MCP tools over JSON format
- Phase 3: Resources added for real-time program state
- Phase 4: Streamable HTTP transport for external agent connections

## Relation to madrac-recon (future)

madrac-recon is planned to include:

- Voice cloning for personalized TTS (Coqui TTS or StyleTTS2, requires ~30 min clean audio from user)
- Custom wakeword training with user voice data

These will be exposed as MCP tools once recon is implemented. MCP is the integration layer that connects recon's capabilities to the rest of the ecosystem.

## Decision

PENDING — human to decide between Options A, B, or C.

## Constraints

- New dependency: mcp SDK (pip install mcp, pure Python, lightweight)
- Must not break existing ejecutar_accion() in core/actions.py
- Must not increase .exe size significantly (mcp SDK is pure Python)
