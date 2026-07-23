# ADR-007 — Distribution Strategy: PyInstaller vs Nuitka

**Date**: 2026-07-01  
**Status**: Accepted — PyInstaller onefile confirmed as production strategy  
**Decision Makers**: Engineering team  
**Components Affected**: madrac-dubs build process

---

## Context

Currently, madrac-dubs uses PyInstaller to create a frozen executable for Windows. This works but has known issues:
- `demucs/remote/files.txt` not bundled automatically (requires explicit `datas=`)
- Startup time is slow (UPX compression/decompression)
- Binary size is large (~500 MB+)
- No GPU optimization hints

Alternative: **Nuitka** (AOT C compiler for Python)
- Compiles Python to C, then to native binary
- Potentially faster startup
- Smaller binary size
- Better compatibility with native extensions (PyTorch, Demucs)

---

## Decision to Make

**Question**: Should madrac-dubs switch from PyInstaller to Nuitka as the primary distribution strategy?

**Constraints**:
- Must work with PyTorch, Demucs, Edge TTS, FFmpeg, PySide6
- Windows 11 target only
- Distribution must be reliable (no crashes on first run)

---

## Evidence-Gathering Phase (Engineering Sprint 001)

**Goal**: Build madrac-dubs with Nuitka, discover problems.

**Success Criteria**:
1. ✅ Nuitka build compiles without errors
2. ✅ Build runs: `madrac-dubbing-nuitka.exe api --port 5000`
3. ✅ Health check works: `GET /health` returns ok
4. ✅ Submit job works: `POST /dubbing` accepts and starts processing
5. ✅ Demucs separation works (if available)
6. ✅ Output MKV file created successfully

**Failure Cases** (document, don't panic):
- Compilation fails → document error, consider workaround
- Runtime crash → debug and fix
- Missing DLLs → add to build script
- Demucs import fails → investigate

---

## Build Plan

### Step 1: Install Nuitka
```bash
pip install nuitka zstandard
```

### Step 2: Create build script
```bash
python -m nuitka \
  --onedir \
  --windows-console-mode=attach \
  --include-package-data=madrac_dubbing \
  --include-package-data=demucs \
  src/madrac_dubbing/__main__.py \
  -o dist/madrac-dubbing-nuitka
```

### Step 3: Run test (health check)
```bash
dist/madrac-dubbing-nuitka.exe api --port 5000 &
curl http://127.0.0.1:5000/health
```

### Step 4: Document results
- If success: create NUITKA_BUILD_SUCCESS.md
- If failure: create NUITKA_BUILD_ISSUES.md

---

## Current Status

**PyInstaller**:
- Working (with ADR-006 Opción A applied)
- Demucs supported (bundle includes `files.txt`)
- Known issue: Startup slow, binary large

**Nuitka**:
- Not tested yet (this decision ADR initiates testing)
- Potentially better, but unknown compatibility

---

## Timeline

- **Now (Sprint 001)**: Build with Nuitka, gather evidence
- **Based on results**: Either adopt Nuitka or confirm PyInstaller as standard
- **Final decision**: After build testing + documentation

---

## Recommendation (Preliminary)

Start with Nuitka build attempt. If it works → adopt as new standard. If it fails → document issue and stay with PyInstaller (which already works).

**Risk**: Low (PyInstaller is always an option to revert to)

---

## Decision

PyInstaller onefile is the confirmed distribution strategy for all MADRAC desktop components. This decision was made by default — the build works, 290 tests pass, the assistant runs integrated, and the .exe is the distributed artifact.

**Current state**: MADRAC-SUBS.exe ~601 MB via madrac-subs-v3-onefile.spec

Nuitka was never tested and is not a current priority.

## Open Items (not blockers)

- ADR-006 Option A still pending: adding demucs/remote/ to datas= in the .spec so Demucs AI works in the .exe. Current .exe uses DSP fallback only.
- Future consideration: migrate to --onedir if startup time becomes a problem.
- Nuitka remains documented as a future investigation path if PyInstaller limitations become critical.
