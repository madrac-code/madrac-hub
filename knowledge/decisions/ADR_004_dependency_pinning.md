# ADR-004 — Dependency Pinning Strategy

**Date**: 2026-06-24 (applied in SUBS), 2026-06-26 (documented as standard)  
**Status**: Accepted — must be applied from day 1 of each component  
**Deciders**: Human  
**Components affected**: SUBS, ASISTENTE, DUBS, all future components

## Context

In MADRAC-SUBS, dependency versions were pinned in commit 36408cc ("Phase 1.6: Pin critical dependency versions") — this occurred near the END of the development cycle. During all prior development, versions were floating, making environment reproduction fragile.

## Decision

Dependencies must be pinned in the FIRST requirements.txt of every component. Not in a Phase 1.6. Not at the end. On day one.

## Required for each new component

```
# requirements.txt — always pin exact versions from the start
faster-whisper==1.0.2       # pin immediately
torch==2.5.1+cpu            # pin immediately
transformers==4.35.2        # pin immediately
PySide6==6.8.0              # pin immediately
```

## Lessons Learned

Floating versions in ML projects are especially dangerous because:
- torch minor versions can break CTranslate2 compatibility
- transformers updates frequently break model loading APIs
- PySide6 and torch can conflict on import order

The cost of pinning late: environment cannot be reproduced reliably.
The cost of pinning early: none.
