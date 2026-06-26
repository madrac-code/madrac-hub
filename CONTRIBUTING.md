# Contributing to MADRAC-HUB

## Repository Structure

This repository has two distinct worlds:

### /knowledge — Structural (do not modify without an ADR)
Contains the architecture, decisions, research, and methodology that define the project. Changes here require a documented decision.

### /development — Living (update freely as part of normal workflow)
Contains prompts, context files, phase tracking, postmortems, and specifications. These are updated constantly.

### /runtime — Future (Phase 1+, do not touch in Phase 0)
Will contain the Event Bus, IPC Layer, and plugin system.

---

## Before Every Development Session

1. Read `development/phases/PHASE_N_CURRENT.md`
2. Check if any context files are stale
3. Prepare your context stack (see CONTEXT_ENGINEERING.md)

## After Every Development Session

1. Commit all changes (even documentation-only changes)
2. Update phase file if objectives were completed
3. Write an ADR if an architectural decision was made
4. Update any context files that are now stale

## ADR Process

Any decision that affects architecture, technology choice, or development methodology gets an ADR in `knowledge/decisions/`. Use ADR_000_template.md.

Number ADRs sequentially. Never delete an ADR — deprecate it and reference the superseding ADR.

## Commit Convention

```
type(scope): description

Types: feat | fix | docs | chore | decision | phase | postmortem
Scopes: knowledge | development | runtime | hub

Examples:
docs(knowledge): add ADR-005 for Event Bus technology choice
phase(development): complete Phase 0 objectives
decision(knowledge): deprecate ADR-001, superseded by ADR-006
```

## The Arbitration Pattern

When multiple AI models give conflicting answers:

1. Document what each proposed
2. Evaluate trade-offs
3. Make the decision
4. Record it in an ADR if it affects architecture
