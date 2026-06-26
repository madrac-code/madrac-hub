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

**Status**: IN PROGRESS (Build Session 001 complete)  
**Next**: Build Session 002 — "Dub Now" button in SUBS  
See `development/phases/PHASE_1_SUBS_DUBS.md` for details.
