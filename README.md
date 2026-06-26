# MADRAC-HUB

Central coordination repository for the MADRAC ecosystem.

## The Ecosystem

| Component | Description | Status |
|-----------|-------------|--------|
| [madrac-subs](https://github.com/madrac-code/madrac-subs) | Subtitle engine — Whisper + PySide6 | v3.0.0-rc1 |
| [madrac-subs-web](https://github.com/madrac-code/madrac-subs-web) | Web frontend — Vercel + Supabase | v2.x |
| [madrac-asistente](https://github.com/madrac-code/madrac-asistente) | Voice assistant — Ollama + JARVIS | v3.2.0 |
| [madrac-dubs](https://github.com/madrac-code/madrac-dubs) | Dubbing engine — Edge TTS + Flask | v1.0-rc1 |
| madrac-hub | Coordinator + knowledge base | Phase 0 |

## Repository Structure

```
knowledge/          ← Structural documents (ADRs, architecture, methodology)
development/        ← Living documents (prompts, context, phases, specs)
runtime/            ← Future: Event Bus + IPC Layer (Phase 1+)
```

## Current Phase

**Phase 0 — Knowledge Foundation**

Establishing the knowledge management system and documenting lessons learned before implementing the runtime layer.

See `development/phases/PHASE_0_FOUNDATION.md` for details.

## Quick Start for AI Agents

If you are an AI agent working in this repository:

1. Read `knowledge/methodology/CONTEXT_ENGINEERING.md`
2. Read `development/phases/PHASE_0_FOUNDATION.md`
3. Check `knowledge/decisions/` for active ADRs
4. Never modify `knowledge/` without an ADR
5. Never touch `runtime/` until Phase 1 is started
