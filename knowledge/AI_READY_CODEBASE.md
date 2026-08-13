# MADRAC — AI-Ready Codebase Guide

This document exists so that any AI agent can understand,
modify, and extend MADRAC with minimal context.
Read this before making any change to the codebase.

## The Pattern (applies to every feature)

Every capability in MADRAC follows this structure:
  Tool (mcp/tools/) → what the system can do (external API)
  Manager (ui/mui/, assistant/, dubbing/) → how it is coordinated
  Stage (pipeline/stages/) → where work actually happens
  SharedWorkspace → where results are persisted

To add a new capability:
  1. Add tool in mcp/tools/<domain>.py
  2. Register in mcp/server.py + mcp/http_server.py + mcp/tool_schemas.py
  3. Implement in the appropriate manager or stage
  4. Write to SharedWorkspace if result should persist
  5. Write tests in tests/test_<domain>.py
  6. Write ADR if it is an architectural decision

## Component Map

### Entry Points
  src/madrac_subs/src/madrac/cli/main.py     — app entry point
  src/madrac_subs/run_mcp.py                 — stdio MCP (Claude Desktop)
  src/madrac_subs/src/madrac/mcp/http_server.py — HTTP MCP (auto-started
                                                   by MainWindow with real
                                                   app_state on port 7654)

### MCP Tools (one file per domain)
  mcp/tools/queue.py          — queue management
  mcp/tools/transcription.py  — Whisper transcription
  mcp/tools/translation.py    — subtitle translation
  mcp/tools/dubbing.py        — dubbing jobs
  mcp/tools/assistant.py      — JARVIS assistant actions
  mcp/tools/config.py         — configuration read
  mcp/tools/workspace.py      — SharedWorkspace access
  mcp/tools/ui.py             — MUI procedural windows

### MUI Protocol (procedural windows)
  ui/mui/manager.py  — UIManager QObject (always active, thread-safe)
  ui/mui/factory.py  — widget factory (6 types: label/button/table/
                        audio_player/waveform/segment_selector)
  ui/mui/events.py   — per-window event queues (thread-safe)

### Processing Pipeline (one file per stage)
  pipeline/stages/audio.py      — extracts audio → writes audio_whisper.wav
  pipeline/stages/transcribe.py — Whisper → writes segments.json
  pipeline/stages/translate.py  — translation → updates segments.json
  pipeline/stages/community.py  — Supabase upload/download
  pipeline/stages/format.py     — SRT formatting
  pipeline/stages/mux.py        — video muxing

### Storage
  workspace/shared.py — SharedWorkspace
  Root: ~/.cache/madrac/workspace/jobs/<sha256-hash>/
  Files: audio_whisper.wav, segments.json, stems/vocals.wav,
         stems/background.wav, dubbed/seg_NNNN.wav,
         ui_state.json, metadata.json

### Configuration
  config/defaults.py — all default values (edit here for new settings)
  config/schema.py   — validation rules
  config/manager.py  — singleton access via get_config()/set_config()
  User config: ~/.cache/madrac-subs/config.json (gitignored)

## How to Add a New MCP Tool

Step 1 — mcp/tools/<domain>.py:
  def my_tool(app_state: dict):
      async def _my_tool(param: str) -> dict:
          """Description shown to AI agents in tool schemas."""
          return {"result": ...}
      return _my_tool

Step 2 — mcp/server.py:
  from .tools.domain import my_tool
  mcp.tool()(my_tool(app_state))

Step 3 — mcp/http_server.py in tool_map:
  "my_tool": my_tool(self.app_state),

Step 4 — mcp/tool_schemas.py:
  {"type": "function", "function": {
      "name": "my_tool",
      "description": "...",
      "parameters": {"type": "object",
                     "properties": {"param": {"type": "string"}},
                     "required": ["param"]}}}

Step 5 — Write tests in tests/test_<domain>.py
Step 6 — Write ADR if this is architectural

## How to Add a New MUI Widget Type

Step 1 — ui/mui/factory.py:
  elif wtype == "my_widget":
      return _make_my_widget(descriptor, on_event, wid)
  def _make_my_widget(d, on_event, wid): ...

Step 2 — Document in this file under Supported Widget Types
Step 3 — Update create_window tool schema description

## Supported Widget Types (Phase 1)

  label            — static text, optional bold/align
  button           — triggers MCP tool or internal action
                     action: {"tool": "tool_name", "params": {...}}
                     action: {"internal": "play_segment"|
                              "record_segment"|"close_window"}
  table            — read-only tabular data, columns + rows
  segment_selector — list of {id, start, end, text} segments, selectable
  audio_player     — play/pause + position slider for a wav file
  waveform         — visual placeholder (Phase 1), shows file path

## Known Limitations

LLAVE-005 (audio):
  PortAudio blocking mode (sd.InputStream) fails on most Windows
  devices. Use sd.rec() + resample instead.
  See: ui/mui/manager.py record_segment()

scipy in .exe:
  scipy excluded from PyInstaller spec (size constraint).
  manager.py imports deferred with numpy fallback.
  To add scipy: edit madrac-subs-v3-onefile.spec hiddenimports.

Claude Desktop vs HTTP MCP:
  Claude Desktop uses stdio (run_mcp.py) — UIManager and
  queue_manager are not available (standalone mode).
  OpenCode and external agents use HTTP (127.0.0.1:7654) — full state.
  TODO: claude_desktop_config.json should point to HTTP when exe is
  running. Currently requires manual switch.

Supabase RLS (ADR-002):
  RLS policies applied but cross-user isolation not tested.
  Do not enable community features publicly until ADR-002 done.

## Pending Work for Future Sessions

HIGH PRIORITY:
  [ ] ADR-002: Supabase RLS cross-user isolation tests
  [ ] LLAVE-005: replace sd.InputStream with sd.rec() globally
  [ ] Claude Desktop: auto-detect HTTP vs stdio based on port 7654

MEDIUM PRIORITY:
  [ ] ADR-006 Option A: bundle Demucs in PyInstaller spec
  [ ] MUI Phase 2: timeline widget + mixer + keybindings (Space=record)
  [ ] RECON component: 3-channel audio editor (background/dubbed/mix)
  [ ] madrac-recon: voice cloning + custom wakeword training

LOW PRIORITY:
  [ ] MUI Phase 3: community templates in madrac-subs-web
  [ ] Event Bus / MADRAC-CORE (bottom-up from SUBS→DUBS integration)
  [ ] Plugin system for pipeline stages
  [ ] Auto-update mechanism

## Test Command

  cd D:\madrac-hub
  set PYTHONPATH=src\madrac_subs\src
  set QT_QPA_PLATFORM=offscreen
  pytest src/madrac_subs/tests/ --tb=short -q

Expected: 410+ tests passing. Never commit with failures.

## ADR Registry

ADR-001  PyInstaller distribution (Deprecated — DO NOT repeat)
ADR-002  Supabase RLS (OPEN RISK)
ADR-006  Demucs frozen .exe bug (Option A pending)
ADR-007  PyInstaller confirmed as production strategy
ADR-008  MCP server Phases 3A-3C (implemented)
ADR-009  Assistant in-process integration
ADR-010  Hybrid monorepo structure
ADR-011  MUI Protocol — procedural windows via MCP