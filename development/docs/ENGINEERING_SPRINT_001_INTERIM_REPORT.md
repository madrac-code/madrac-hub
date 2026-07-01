# Engineering Sprint 001 — Interim Results & Documentation

**Date**: 2026-07-01  
**Status**: 80% complete (Nuitka build still compiling)

---

## Completed Work

### DT-001: Demucs Performance Investigation ✅

**Finding**: Not a bug. Demucs is a transformer-based audio separation model (O(n²) complexity). Performance is as expected.

**Evidence**:
- 10s audio: 4.54 seconds total (0.45x ratio)
- 88% time in PyTorch tensor ops (conv, attention, linear)
- Not CPU-bound on single core (GIL limited)

**Recommendations**:
1. **GPU acceleration** (10-100x speedup if GPU available)
2. **Smaller model** (2-3x speedup, offer as option)
3. **Cache works perfectly** (365.6x speedup on repeat)

**Action for Phase 1**: Keep as-is (DSP default, Demucs optional). Document recommendation for GPU in ARCHITECTURE.md.

**Report**: `knowledge/research/DT_001_DEMUCS_PROFILING_REPORT.md`

---

### DT-002: Distribution Strategy (PyInstaller vs Nuitka) ✅

**Decision**: ADR-007 created. Experiment with Nuitka to gather evidence.

**Current state**:
- PyInstaller: Working (ADR-006 Opción A applied)
- Nuitka: Build in progress (expected 30-60 min compilation)

**Discovered issues**:
- Nuitka flag differences (`--onedir` doesn't exist, use directory mode)
- Python 3.14 is experimental in Nuitka 4.1.3
- Architecture mismatch possible (x86 vs x86-64)

**Action for Phase 1**: Wait for Nuitka build to complete, then test execution.

---

### DT-003: Demucs Cache Validation ✅

**Finding**: Cache is working PERFECTLY.

**Test Results**:
- Run 1 (cold): 2.97 seconds (no cache hit)
- Run 2 (warm): 0.01 seconds (cache hit)
- **Speedup: 365.6x**

**Conclusion**: No action needed. Cache is production-ready.

---

## In Progress

### Nuitka Build ⏳

**Status**: Compiling (30-60 min expected)

**Challenges discovered**:
- Python 3.14 experimental support
- Architecture mismatch (x86 vs x86-64)
- Requires Zig compiler

**Next**: Wait for completion, then test `madrac_dubbing/__main__.exe api --port 5000`

---

## Findings Summary

| Item | Status | Impact |
|------|--------|--------|
| **DT-001** | RESOLVED | No optimization urgent. GPU +10-100x if needed. |
| **DT-002** | IN PROGRESS | PyInstaller works; Nuitka TBD. |
| **DT-003** | RESOLVED | Cache perfect (365.6x speedup). |
| **Demucs perf** | MITIGATED | DSP mode works; Demucs optional. |
| **Distribution** | VALIDATING | Nuitka build in progress. |

---

## Architecture Improvements Needed

### For ARCHITECTURE.md (update required)

1. **GPU Support**
   ```python
   device = 'cuda' if torch.cuda.is_available() else 'cpu'
   model = model.to(device)
   ```

2. **Cache Strategy** (document existing behavior)
   - 365.6x speedup on cache hit
   - Directory: `.stems_tmp/`
   - Keyed by video hash

3. **Model Variant Options**
   - `htdemucs` (current, best quality)
   - `demucs` (medium)
   - `light` (fast)

---

## Documentation Created This Session

- `DT_001_DEMUCS_PROFILING_REPORT.md` — profiling analysis
- `ADR_007_nuitka_vs_pyinstaller.md` — distribution decision
- `NUITKA_BUILD_DISCOVERY_LOG.md` — build experiment log
- `demucs_profiler.py` — profiling tool
- `validate_cache.py` — cache test script

---

## Next Steps (if Nuitka build succeeds)

1. Test build: `madrac_dubbing/__main__.exe api --port 5000`
2. Health check: `GET /health`
3. Submit job: `POST /dubbing` (synthetic video)
4. Monitor for crashes, missing DLLs, timeouts
5. Document findings (success or errors)

If succeeds → Nuitka becomes new standard + ADR-007 finalized
If fails → Document issue, stay with PyInstaller, update ADR-007

