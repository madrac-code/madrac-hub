# Phase 2 — Assistant + Dubbing Integration

**Status**: COMPLETE
**Completed**: 2026-07-23 (commit ecc566a)
**Previous phase**: PHASE_1_RUNTIME.md

## What Was Done

### Phase 2A — Dubbing Integration (SUBS → DUBS)
- DubbingManager + DubDialog added to main_window
- "Dub Now" button integrated in SUBS Qt UI
- End-to-end pipeline: audio extraction → TTS (45 segments) → Demucs → mix → mux
- Waitress replaced Flask dev server (threads=8, non-blocking)
- WindowsSelectorEventLoopPolicy fix for edge-tts errno 22 on Windows
- Demucs frozen .exe bug: fallback --dubs-python applied (ADR-006)

### Phase 2B — Code Pruning
- app_log.py, subtitle_formatter.py, utils.py removed
- Paths unified: get_user_config_dir() in madrac_integration.py and workspace/manager.py

### Phase 2C — Assistant Integration (SUBS + ASISTENTE)
- AssistantManager (QObject, daemon thread) integrated into SUBS
- asistente.py refactored for headless mode (gui=None)
- Tkinter lazy import fix applied
- AssistantConfigDialog added to SUBS ConfigDialog (3 tabs)
- Config shared via TOML overlay
- 13 new tests in test_assistant.py

### Monorepo Layer Added
- src/madrac_asistente/ — full assistant code versioned in HUB
- src/madrac_dubbing/ — full dubbing code versioned in HUB
- Upstream repos remain autonomous (see ADR-010)

### CI/CD
- .github/workflows/ci.yml — unified pipeline for SUBS + ASISTENTE
- .github/workflows/build-linux.sh — Linux build
- dev-requirements.txt — development dependencies

### Knowledge Documents
- LLAVE_003 — Serverless rate limiting
- LLAVE_004 — Supabase RLS audit
- ADR-007 closed (PyInstaller confirmed)
- ADR-008 created (MCP proposal)
- ADR-009 created (assistant integration)
- ADR-010 created (hybrid monorepo)

## Known Issues Carried Forward

| Issue | Status | ADR |
|-------|--------|-----|
| Demucs >10 min for 36s video | Open | ADR-006 |
| Demucs .exe frozen | Workaround (--dubs-python) | ADR-006 |
| Supabase RLS insufficient | Open, not urgent | ADR-002 |
| HUB src/ sync with upstream | Manual, no automation | ADR-010 |

## Exit Criteria Met

- [x] SUBS + ASISTENTE run as single .exe
- [x] "Dub Now" pipeline functional end-to-end
- [x] 290 SUBS tests + 13 assistant tests + 14 dubbing tests pass
- [x] CI/CD pipeline active
- [x] Documentation synced with ADR-009, ADR-010, this phase doc

## Next Phase

PHASE_3_MCP.md — MCP Server for assistant tools and external agency
