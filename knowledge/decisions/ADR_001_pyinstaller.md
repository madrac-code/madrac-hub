# ADR-001 — PyInstaller as Distribution Strategy for Torch-based Apps

**Date**: 2026-05-28 (applied), 2026-06-26 (documented)  
**Status**: Deprecated — DO NOT repeat this pattern  
**Deciders**: Human (prior experience bias) + AI (reproduced assumption from prompts)  
**Components affected**: SUBS, ASISTENTE, DUBS

## Context

All three components require distribution to Windows users as standalone executables. The stack includes PyTorch, CTranslate2, PySide6, and faster-whisper — all of which have C extensions and native binaries.

## Options Considered

| Option | Proposed by | Pros | Cons |
|--------|-------------|------|------|
| PyInstaller | Human (inertia) | Familiar, single .exe | Incompatible with Torch+CTranslate2 when console=False |
| venv + launcher .bat | — | Stable, trivial, zero packaging bugs | Less "clean" UX |
| Nuitka | — | Real compilation, C extension compatible | Slower build, less familiar |
| conda-pack | — | Designed for torch/numpy environments | Requires conda ecosystem |
| Docker | — | Zero environment issues | Overkill for desktop GUI app |

## Decision

PyInstaller was chosen due to developer familiarity and because AI agents kept reproducing the assumption when PyInstaller was mentioned in prompts.

## Consequences

### Positive
- Single .exe distribution works in simple cases

### Negative
- 5+ fix commits related to build failures
- 11 error log files generated during debugging
- Torch Frozen Bug: critical, unresolved as of 2026-06-25
- `console=False` incompatible with CTranslate2 — never fully resolved
- Current workaround: venv-based distribution (what should have been used)

## Lessons Learned

1. When AI agents reproduce a technical assumption from the prompt, challenge it explicitly. Ask: "What are the alternatives to PyInstaller for this stack?"
2. Pin distribution strategy in the first week of a new component.
3. If the workaround IS the original alternative, the original decision was wrong.
4. The correct approach for torch+PySide6 on Windows: venv + iniciar.bat launcher.

## Current Status

All three components currently use venv + .bat as the actual distribution method. PyInstaller .spec files remain but are not the primary distribution path. Future components should NOT use PyInstaller with torch.
