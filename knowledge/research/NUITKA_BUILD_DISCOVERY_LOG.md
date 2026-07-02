# Nuitka Build Discovery Log — Engineering Sprint 001

**Date**: 2026-07-01  
**Component**: madrac-dubs (distribution build)  
**Topic**: Nuitka compilation experiment

---

## Attempt 1: Initial Build (FAILED)

### Error
```
nuitka: error: no such option: --onedir
```

### Cause
Nuitka doesn't have `--onedir` flag (that's PyInstaller).

Nuitka behavior:
- `--onefile` → single executable (not suitable for dependencies)
- Default (no flag) → directory with executable + dependencies (what we want)

### Resolution
Removed `--onedir`, used directory mode (default).

### Lesson (for LLAVE)
Different build tools have different flags. PyInstaller and Nuitka are NOT API-compatible. Need wrapper script that abstracts differences.

---

## Attempt 2: Corrected Build (IN PROGRESS)

**Command**:
```bash
python -m nuitka \
  --windows-console-mode=attach \
  --include-package-data=madrac_dubbing \
  --include-package-data=demucs \
  --follow-imports \
  --python-flag=-u \
  src/madrac_dubbing/__main__.py
```

**Expected output**: `src/madrac_dubbing/__main__.dist/` directory with executable

**Status**: Compiling...

---

## Expected Issues & Mitigation

| Issue | Likelihood | Mitigation |
|-------|------------|-----------|
| PyTorch linking fails | MEDIUM | Check compiler flags, might need MSVC |
| Demucs data files missing | HIGH | `--include-package-data=demucs` should handle |
| Edge TTS asyncio issues | LOW | Already fixed in code (WindowsSelectorEventLoopPolicy) |
| FFmpeg not found | MEDIUM | Nuitka might not bundle; add to PATH |
| PySide6 plugins | MEDIUM | May need explicit inclusion of Qt plugins |
| Compilation time | CERTAIN | Nuitka is much slower than PyInstaller (~30-60 min) |

---

## Next: Validation Plan

Once build completes:

1. **Health check**: `build/madrac_dubbing/__main__.exe api --port 5000 & curl /health`
2. **Job submission**: `POST /dubbing` with synthetic video + SRT
3. **Monitor for**: crashes, missing DLLs, import errors

---

## Key Differences: PyInstaller vs Nuitka

| Aspect | PyInstaller | Nuitka |
|--------|-------------|--------|
| Build time | Fast (~5 min) | Slow (~30-60 min) |
| Output type | Single EXE or DIR | DIR with .exe + .dll/.so |
| Binary size | Large (~500 MB with UPX) | Smaller (C optimization) |
| Startup time | Slow (UPX decompress) | Fast (native code) |
| Data file bundling | `datas=` explicit | `--include-package-data` |
| Debugging | Easier (zipimport) | Harder (native code) |

