# LLAVE: Python 3.14 Compatibility with Dependencies

**Date**: 2026-07-01  
**Priority**: MEDIUM  
**Status**: RESOLVED (with version updates)

---

## Issue

Validation script failed during `pip install -r requirements.txt`:

```
ERROR: Could not find a version that satisfies the requirement ctranslate2==4.3.1
ERROR: No matching distribution found for ctranslate2==4.3.1
```

AND

```
ERROR: PySide6 6.8.0 requires Python <3.14
```

---

## Root Cause

1. **ctranslate2==4.3.1** is end-of-life (EOL). Current versions: 4.6.1+
2. **PySide6 6.8.0** only supports Python 3.9-3.13. Python 3.14 is experimental.

---

## Solution

Updated `D:\madrac-hub\requirements.txt`:

**Before**:
```
PySide6>=6.8.0
ctranslate2==4.3.1
```

**After**:
```
PySide6>=6.11.0  # Python 3.14 compatible
ctranslate2>=4.6.1  # Latest available
```

---

## Trade-off

**Risk**: Different versions than madrac-subs was tested with.

**Mitigation**: 
- ctranslate2 4.6.1+ is backward compatible (minor version bump)
- PySide6 6.11.0 is newer, likely more stable
- Running tests will verify compatibility

---

## Related

- ADR_008 (monorepo integration)
- Python 3.14 experimental support noted in Nuitka warnings (earlier session)

---

## Action Items

- [x] Update requirements.txt
- [ ] Re-run validation script
- [ ] Monitor for behavioral changes in tests
- [ ] Consider pinning to Python 3.13 if 3.14 issues persist

---

## Related: PyAV (av) Build Failure

Another issue surfaced during `pip install`:

**Symptom**: `fatal error C1083: No se puede abrir el archivo incluir: 'libavutil/mathematics.h'` — PyAV fails to compile from source.

**Root Cause**: `faster-whisper==1.0.2` requires `av>=11,<13`. PyAV 11-12 have no wheel for Python 3.14 on Windows; they need FFmpeg C headers to build.

**Fix**: Updated `faster-whisper==1.0.2` to `>=1.2.0`. This drops the `<13` pin, allowing `av>=17` which has a `cp311-abi3-win_amd64` wheel compatible with Python 3.14+.

**Lesson**: `abi3` wheels (tag `cp311-abi3-*`) work on Python 3.11+. Before pinning packages with C extensions, verify wheel availability for the target Python version.

## Decision

**ACCEPT** version updates. Benefits (Python 3.14 compatibility + latest packages) outweigh risk (minor version bumps).

If tests fail post-update, roll back to pinned versions + Python 3.13.

