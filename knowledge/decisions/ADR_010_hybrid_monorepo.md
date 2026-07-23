# ADR-010 — Hybrid Monorepo: HUB Orchestrates Autonomous Repos

**Date**: 2026-07-23
**Status**: Accepted — implemented
**Deciders**: Human
**Components affected**: ALL

## Context

As the ecosystem grew, a decision was needed about repository structure:
- Option A: True monorepo — all code in madrac-hub, remove separate repos
- Option B: Stay with separate repos — no central coordination
- Option C: Hybrid — separate repos remain autonomous, HUB adds an orchestration layer

## Decision

Option C: Hybrid structure.

Each component retains its own git repository and can be developed, built, and distributed independently:
- D:\madrac-subs → github.com/madrac-code/madrac-subs
- D:\madrac-asistente → github.com/madrac-code/madrac-asistente
- D:\madrac-dubs → github.com/madrac-code/madrac-dubs
- D:\madrac-subs-web → github.com/madrac-code/madrac-subs-web

madrac-hub ALSO contains copies under src/:
- src/madrac_subs/ — copy of SUBS for integrated build
- src/madrac_asistente/ — copy of ASISTENTE for integrated build
- src/madrac_dubbing/ — copy of DUBS for integrated build

HUB's src/ layer is used for:
- Unified test suite across all components
- Integrated build (.exe that includes SUBS + ASISTENTE)
- CI/CD pipeline (.github/workflows/)
- Cross-component integration tests

## Sync Responsibility

The human developer is responsible for keeping src/ copies in HUB in sync with the upstream repos. There is no automated sync yet.

**Risk**: src/ copies can drift from upstream repos.
**Mitigation**: Run upstream pulls before any HUB build session.

## Consequences

### Positive
- Components remain independently deployable and versioned
- HUB can run integration tests without affecting component repos
- Single build entry point for the combined product

### Negative
- Code duplication between component repos and HUB src/
- Manual sync required — no automation yet
- Potential for HUB src/ to drift from upstream

## Future

When MADRAC-CORE Event Bus is implemented (Phase 3+), the sync problem may be solved via git submodules or a proper monorepo migration. This ADR should be revisited at that point.
