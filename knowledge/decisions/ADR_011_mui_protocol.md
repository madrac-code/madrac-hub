# ADR-011 — MADRAC UI Protocol (MUI): Procedural Window Generation via MCP

**Date**: 2026-08-10
**Status**: Accepted — Phase 1 in progress
**Deciders**: Human
**Components affected**: SUBS, HUB, future: SUBS-WEB

## Context

The MCP server (Phase 3C) gives external agents control over 
MADRAC's processing pipeline. The next evolution is giving agents 
the ability to create task-specific UI workstations on demand.

A user can tell an agent: "dub character X from this video" and 
the agent should be able to:
1. Process the video (transcription, diarization, stem separation)
2. Create a custom UI workstation with the relevant controls
3. Let the user work interactively (record, play, review)
4. React to user interactions via event polling

## Decision

Implement MADRAC UI Protocol (MUI) as a layer on top of the 
existing MCP server. Agents create windows via MCP tools; 
windows run in the Qt main thread via thread-safe signals; 
user interactions are exposed back to agents via event polling.

## Architecture

### Thread Safety
All widget creation/modification happens in the Qt main thread.
MCP tools emit Qt signals; UIManager (QObject) receives them 
and creates/updates widgets.

### Window State Persistence
Each window is associated with a job_id. State is saved to:
  ~/.cache/madrac/workspace/jobs/<job_id>/ui_state.json
Agents can restore windows across sessions.

### Bidirectional Events
User interactions (button clicks, segment selection, key presses)
are queued as events. Agents poll via:
  get_window_events(window_id) → list of pending events

### Security
- Agents cannot execute arbitrary code
- Button actions are restricted to a whitelist:
  * Any registered MCP tool name
  * Internal actions: play_segment, record_segment, close_window
- Maximum 5 simultaneous windows per session
- Windows owned by session; orphaned windows auto-close after 10min

## Phase 1 Scope (current)

Widgets: label, button, table, audio_player, waveform, segment_selector
MCP Tools: create_window, update_widget, close_window, 
           list_windows, get_window_events

## Phase 2 Scope (future)

Widgets: timeline, mixer, keybinding_handler
Use case: dubbing workstation per character

## Phase 3 Scope (future)

Community templates: publish/download window layouts via 
madrac-subs-web Supabase table ui_templates

## Consequences

### Positive
- Agents can build task-specific interfaces without developer work
- Community can share workflow templates
- Foundation for MADRAC as an extensible platform

### Negative  
- Qt thread safety requires careful signal/slot design
- Event polling adds latency to bidirectional interaction
- Increased complexity in SUBS main window management

## Files to Create (Phase 1)

src/madrac_subs/src/madrac/ui/mui/
    __init__.py
    manager.py          ← UIManager QObject + WindowRegistry
    factory.py          ← Widget factory (creates Qt widgets from JSON)
    events.py           ← Event queue per window
    
src/madrac_subs/src/madrac/mcp/tools/ui.py
    ← create_window, update_widget, close_window, 
      list_windows, get_window_events
