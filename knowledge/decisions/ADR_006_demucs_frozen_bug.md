# ADR-006 — Demucs Frozen-in-Exe Bug & `has_demucs()` Fix

**Date**: 2026-06-26
**Status**: Partially resolved — Opción B applied, Opción A pending
**Deciders**: Human + Claude + OpenCode
**Components affected**: DUBS

## Context

During Phase 1 Build Session 001, `dubs_integration_test.py` failed with:

```
FileNotFoundError: _MEI43122\demucs\remote\files.txt
```

`_MEI43122` is a PyInstaller temp directory that only exists while the
frozen `.exe` is running. The error occurred because:

1. `has_demucs()` in `separation.py:140` caught only `ImportError`
2. `import demucs` succeeds at import time (module-level `pretrained.py`
   defines `REMOTE_ROOT = Path(__file__).parent / 'remote'` but does not
   read `files.txt` yet)
3. `has_demucs()` returns `True`
4. `separate_stems()` calls `_separate.main()` → `get_model()` →
   `_parse_remote_files(REMOTE_ROOT / 'files.txt')` → **FileNotFoundError**
   because PyInstaller did not bundle `demucs/remote/files.txt`

The bug affects `madrac-dubbing.exe` (PyInstaller frozen). From the venv,
`files.txt` exists at `venv\Lib\site-packages\demucs\remote\` and the
pipeline works normally.

## Options Considered

| Option | Proposed by | Pros | Cons |
|--------|-------------|------|------|
| **A** — Add `demucs/remote/` to PyInstaller `.spec` (`datas=`) | Claude | Demucs works in frozen `.exe` | Requires rebuild; same pattern as ADR-001 |
| **B** — Catch `FileNotFoundError` in `has_demucs()` | Claude | Robust in any environment; pipeline falls back to DSP; no rebuild needed | Demucs silently disabled in frozen `.exe` |

## Decision

**Opción B** applied in `separation.py:137-145`. The modified function
additionally calls `pretrained._parse_remote_files()` to verify that
`files.txt` is actually readable:

```python
def has_demucs() -> bool:
    try:
        import demucs
        from demucs import pretrained
        pretrained._parse_remote_files(pretrained.REMOTE_ROOT / 'files.txt')
        return True
    except (ImportError, OSError, FileNotFoundError):
        return False
```

Opción A remains as technical debt — see Current Status.

## Consequences

### Positive
- Pipeline no longer crashes when `files.txt` is inaccessible
- Fallback to DSP vocal reduction already existed and works
- Fix is a single-function change in `separation.py`; no ripple effects
- Zero external dependencies or build steps

### Negative
- Demucs AI separation is unavailable in the frozen `.exe` build
- Users of `madrac-dubbing.exe` get lower-quality vocal reduction (DSP)
- Opción A must still be implemented before production release

## Lessons Learned

1. **Feature detection must verify resources, not just imports**.
   `has_demucs()` checked that the Python package is importable, but
   Demucs reads `files.txt` at model-load time (not import time).
   Any similar "detect if X is available" function must test that the
   actual runtime resources are accessible.

2. **PyInstaller does not include data files automatically**.
   Packages that ship manifests, model configs, or other data files
   (like `demucs/remote/*`) need explicit `datas=` entries in the
   `.spec` file. This applies to any package loaded via PyInstaller.

3. **Same pattern as ADR-001 (PyInstaller + torch)**.
   General rule: PyInstaller + ML packages = assume data files are
   NOT bundled until proven otherwise.

## Current Status

- `has_demucs()` corrected — committed in `madrac-dubs`
- `madrac-dubbing.exe` still broken for Demucs (Opción A not implemented)
- Pipeline works from venv with full Demucs AI separation
- Pipeline works from frozen `.exe` with DSP fallback (lower quality)
- `dubs_integration_test.py` passes with `--dubs-python`
