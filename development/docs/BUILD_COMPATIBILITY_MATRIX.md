# BUILD COMPATIBILITY MATRIX — Engineering Sprint 001 Provisional

**Status**: WORK IN PROGRESS (Nuitka build still compiling)  
**Last Updated**: 2026-07-01 session  
**Component**: madrac-dubs (dubbing engine)

---

## Dependency Compatibility Status

### Critical Dependencies

| Dependency | Version | PyInstaller | Nuitka | Notes |
|------------|---------|-------------|--------|-------|
| **PyTorch** | 2.4.x | ✅ WORKS | ⏳ TBD | Large binary, requires UPX exclude list |
| **Demucs** | 4.0.1 | ✅ WORKS (ADR-006) | ⏳ TBD | Needs `files.txt` bundled; `--include-package-data` should handle |
| **Edge TTS** | 6.16.x | ✅ WORKS | ⏳ TBD | Async event loop (Windows fix applied) |
| **FFmpeg** | 7.0+ | ✅ WORKS (PATH) | ⏳ TBD | External binary, not bundled |
| **PySide6** | 6.11.x | ✅ WORKS | ⏳ TBD | Large, may need Qt plugin handling |
| **Flask/Waitress** | 3.1+ / 3.0.0+ | ✅ WORKS | ⏳ TBD | HTTP server, lightweight |
| **CTranslate2** | 4.0+ | ✅ WORKS | ⏳ TBD | ML library, large binary |
| **soundfile/librosa** | - | ✅ WORKS | ⏳ TBD | Audio processing, numpy-based |

### Build Tools

| Tool | Status | Issue |
|------|--------|-------|
| PyInstaller 6.21 | ✅ WORKING | None known |
| Nuitka 4.1.3 | ⏳ COMPILING | Python 3.14 experimental, arch mismatch detected |
| Zig (Nuitka req) | ⏳ DOWNLOADING | Auto-download in progress |
| MSVC Compiler | ⚠️ ARCHITECTURE MISMATCH | x86 vs x86-64 arch detected; may need Intel oneAPI |

---

## Known Issues & Discoveries

### Issue 1: Python 3.14 Experimental Support
**Severity**: LOW  
**Details**: Nuitka 4.1.3 only experimentally supports Python 3.14  
**Recommendation**: Continue for now; may need to downgrade to 3.13 if compilation fails

### Issue 2: Architecture Mismatch
**Severity**: MEDIUM  
**Details**: Python binary is x86-64, MSVC compiler is x86  
**Recommendation**: May need to install x86-64 MSVC or switch to Intel oneAPI compiler

### Issue 3: Large Binary Size Expected
**Severity**: LOW  
**Details**: PyTorch alone is 2GB+; final binary will be large even with Nuitka optimizations  
**Recommendation**: Accept as constraint; UPX compression helps with PyInstaller

---

## Provisional Recommendation

**Decision**: PENDING Nuitka build completion

**If Nuitka build succeeds**:
- Adopt Nuitka as new standard
- ADR-007 finalizes: "Nuitka is distribution strategy"
- Phase 1 **COMPLETE**

**If Nuitka build fails**:
- Document errors in ADR-007
- Continue with PyInstaller (proven to work)
- Defer Nuitka investigation to Phase 3+
- Phase 1 **COMPLETE** (PyInstaller path)

Either way, Phase 1 can be declared complete once build is validated.

---

## Build Time Comparison (Estimated)

| Tool | Time | Size | Notes |
|------|------|------|-------|
| **PyInstaller** | 5-10 min | ~500 MB | UPX compression applied |
| **Nuitka** | 30-60 min | ~300-400 MB | C compilation overhead |

---

## Outstanding Questions

1. Will MSVC x86-64 compiler be needed?
2. Can Python 3.14 be used, or revert to 3.13?
3. How long will Nuitka compilation take (full)
4. Will final binary execute without errors?
5. Are there missing DLL dependencies?

---

## Next Validation Steps

Once Nuitka build completes:

```
1. Check for build output directory: src/madrac_dubbing/__main__.dist/
2. Verify executable exists: __main__.exe
3. Test execution: .\__main__.exe api --port 5000 &
4. Health check: curl http://127.0.0.1:5000/health
5. Submit job: POST /dubbing with synthetic SRT
6. Monitor for errors (missing DLLs, crashes, timeouts)
7. Document results in NUITKA_BUILD_SUCCESS.md or NUITKA_BUILD_ISSUES.md
```

---

## Rollback Plan

If Nuitka fails:
1. PyInstaller builds are still available
2. No changes to Phase 1 functionality
3. Document issue as ADR-007 rejection
4. Declare Phase 1 complete with PyInstaller path

