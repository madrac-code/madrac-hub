# ADR-009 — Assistant Integrated In-Process into MADRAC-SUBS

**Date**: 2026-07-23
**Status**: Accepted — implemented in Phase 2B/2C
**Deciders**: Human
**Components affected**: SUBS, ASISTENTE

## Context

MADRAC-ASISTENTE originally ran as a standalone .exe with its own wakeword loop, Whisper transcription, Ollama IA, and TTS. The question was whether to keep it separate (IPC communication) or integrate it directly into the SUBS process.

## Decision

The assistant runs in-process inside MADRAC-SUBS via AssistantManager (a QObject), launched as a daemon thread. It does not run as a separate .exe.

Integration points:
- AssistantManager.start() / stop() controlled from Qt UI
- Signals: state_changed(bool), error_occurred(str), log_message(str)
- asistente.py runs in headless mode: loop_principal(gui=None, stop_event=Event)
- Config shared via madrac.config (TOML, ~/.cache/madrac-subs/) overlaid with core/config.py JSON

## Why In-Process

- Eliminates IPC complexity for the first integration
- Shared config without file-watching or sync protocols
- Single .exe distribution — user gets assistant + subtitle engine in one binary
- AssistantManager can be disabled cleanly if assistant is not needed

## Consequences

### Positive
- Zero IPC overhead for assistant↔SUBS communication
- Single build artifact
- Config sharing is trivial

### Negative
- A crash in the assistant thread can affect SUBS stability
- Harder to update assistant independently from SUBS
- Tkinter (used in assistant GUI) required lazy import to avoid conflict with PySide6 — tkinter lazy import fix applied

## Relation to Future Architecture

This is a Phase 2 integration decision. In Phase 3+ (MADRAC-CORE), the assistant may be extracted back to a separate process communicating via Event Bus, once the Event Bus exists. This ADR does not prevent that future extraction.

## Files Changed

- src/madrac_subs/src/madrac/assistant/manager.py (new)
- src/madrac_subs/src/madrac/assistant/config.py (new)
- src/madrac_subs/src/madrac/ui/dialogs/assistant_config_dialog.py
- src/madrac_subs/src/madrac/ui/main_window.py
- src/madrac_asistente/asistente.py (headless mode, frozen fix)
