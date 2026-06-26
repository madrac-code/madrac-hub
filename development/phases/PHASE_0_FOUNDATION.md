# Phase 0 — Knowledge Foundation

**Status**: COMPLETE  
**Started**: 2026-06-26  
**Completed**: 2026-06-26  
**Goal**: Establish the knowledge management system before any runtime code

## Objectives

- [x] Define repository structure (knowledge/ + development/ + runtime/)
- [x] Move existing research to knowledge/research/
- [x] Move Contexto.md to knowledge/architecture/MADRAC_CORE_DESIGN.md
- [x] Create ADR system with lessons from existing problems
- [x] Create methodology documentation
- [x] Create prompt and context templates
- [x] Create CONTRIBUTING.md
- [x] First commit + push of complete structure
- [x] Update README.md (5 components including madrac-subs-web)
- [x] Register all ecosystem components (ADR-005)

## What Phase 0 is NOT

Phase 0 does not include:
- Any code in /runtime/
- Event Bus implementation
- IPC Layer
- Integration with SUBS, ASISTENTE, or DUBS

Those belong to Phase 1.

## Exit Criteria

Phase 0 is complete when:
1. All files listed above exist and are populated
2. The structure is committed and pushed to GitHub
3. A new development session can start by reading PHASE_0_FOUNDATION.md and know exactly where the project is

## Phase 1 — SUBS↔DUBS Integration

**Status**: IN PROGRESS (Build Session 002 — debugging)  

### Achieved
- "Dub Now" button in SUBS top bar, connected to DubbingManager and DubDialog
- DUBS API runs in background thread with health check polling
- Pipeline: extract audio → TTS (edge-tts) → Demucs stem separation → mix → mux
- Fixed: `asyncio.ProactorEventLoop` → `WindowsSelectorEventLoopPolicy` (OSError 22 en edge-tts)
- Fixed: `threaded=True` in Flask `app.run()` for concurrent request handling
- End-to-end integration test passes with real video

### Known Issue — Build Session 002 en progreso
Pipeline SUBS → DUBS funciona con video sintético.  
Falla con video real (36s, audio de habla) en el paso extracting_audio.  
Hipótesis: torch/Demucs toma el GIL bloqueando Flask threaded.  
Próxima sesión: diagnosticar con profiler o cambiar a waitress como WSGI server.
