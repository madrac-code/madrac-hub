# Technical Debt — MADRAC Ecosystem

**Last Updated**: 2026-07-01  
**Status**: Active tracking  
**Scope**: Issues that don't block functionality but degrade quality, performance, or maintainability

---

## High Priority (Affects User Experience)

### Issue DT-001: Demucs Performance Optimization

**Severity**: HIGH  
**Component**: madrac-dubs  
**Status**: KNOWN, MITIGATED (not resolved)  
**Impact**: Dubbing process takes 10+ minutes even for 36s videos

**Symptoms**:
- User selects "Alta calidad (Demucs)" checkbox
- Progress shows "reducing_vocals" stage taking 10+ minutes
- UI appears frozen during processing

**Root Cause**:
- Unknown. Hypotheses:
  1. Demucs model loading overhead (~30s per invocation)
  2. Audio padding by TTS creates longer effective audio (hypothesis rejected: tested with 36s, ~380s processed)
  3. GPU not being used efficiently (no GPU utilization metrics taken)
  4. Demucs default settings unoptimized for short audio clips

**Current Mitigation**:
- DSP mode (checkbox OFF) processes in ~0.1x video duration
- Users can toggle between speed/quality

**Investigation Steps**:
1. Profile Demucs with `cProfile` / `py-spy` (identify bottleneck)
2. Check GPU availability and utilization (if user has GPU)
3. Try Demucs model variants (smaller models?)
4. Batch segment processing instead of full audio

**Owner**: TBD (Phase 2+ investigation)  
**Estimated Effort**: 4–8 hours  
**Blocker**: No (workaround exists)

---

### Issue DT-002: ADR-006 Opción A — PyInstaller Demucs Fix

**Severity**: MEDIUM  
**Component**: madrac-dubs (build)  
**Status**: PENDING (Opción B applied, Opción A deferred)  
**Impact**: Frozen .exe uses DSP fallback (lower quality) instead of Demucs AI

**Symptoms**:
- User runs `madrac-dubbing.exe` (frozen with PyInstaller)
- Selects "Alta calidad (Demucs)"
- Gets warning: "Demucs no disponible, usando DSP como fallback"

**Root Cause**:
- PyInstaller doesn't automatically bundle `demucs/remote/files.txt` (data file, not Python module)
- Workaround: `--dubs-python` flag to run from venv

**Current Status**:
- ADR-006 Opción B: Catch FileNotFoundError in `has_demucs()`, fallback to DSP ✅
- ADR-006 Opción A: Add `datas=[...]` to `.spec` file for PyInstaller ⏳

**Fix (Opción A)**:
1. Update `madrac-dubbing.spec` to include:
   ```python
   datas=[
	   (r"venv\Lib\site-packages\demucs\remote", "demucs/remote"),
   ]
   ```
2. Rebuild .exe with `pyinstaller madrac-dubbing.spec`
3. Test that Demucs works in frozen .exe
4. Update build documentation

**Owner**: TBD  
**Estimated Effort**: 1–2 hours (build + test)  
**Blocker**: No (workaround exists; .exe can use DSP)  
**Prerequisite**: DT-001 (optimize Demucs first; no point fixing PyInstaller for slow code)

---

## Medium Priority (Maintainability)

### Issue DT-003: Demucs Cache Invalidation

**Severity**: MEDIUM  
**Component**: madrac-dubs  
**Status**: KNOWN  
**Impact**: Cache hits reported but cache directory not visible; unclear if working

**Description**:
- Demucs separation caches results to disk (see `separation.py`)
- Cache is checked via `video_hash`, which should deduplicate repeated videos
- No tests for cache behavior
- Unknown if cache actually saves time or just takes disk space

**Current State**:
- Cache enabled, metrics reported in `DemucsReport`
- No validation of cache hit rate
- Cache directory location unclear (temporary or persistent?)

**Investigation**:
1. Verify cache directory exists and persists across runs
2. Test cache hit scenario (process same video twice, measure time difference)
3. Consider cache TTL (garbage collection old entries)
4. Document cache behavior in ARCHITECTURE.md

**Owner**: TBD (Phase 2+ optimization)  
**Estimated Effort**: 2–3 hours  
**Blocker**: No

---

### Issue DT-004: LLAVE Documents Organization

**Severity**: MEDIUM  
**Component**: madrac-hub  
**Status**: PARTIALLY ADDRESSED  
**Impact**: Knowledge extraction is ad-hoc; hard to find lessons

**Current State**:
- LLAVE_001_errno22_winsock_asyncio.md created and versioned
- No system for when/how to create new LLAVEs
- No index or discovery mechanism

**Planned Fix**:
1. Create LLAVE_TEMPLATE.md (structure for new LLAVEs)
2. Create LLAVES_INDEX.md (registry of all LLAVEs with dates/authors)
3. Define trigger for creating LLAVE (when? after every bug fix?)
4. Automate extraction: ADRs → LLAVEs pipeline

**Owner**: TBD  
**Estimated Effort**: 2–4 hours  
**Blocker**: No (nice-to-have)

---

### Issue DT-005: madrac-subs Community Feature — Incomplete

**Severity**: MEDIUM  
**Component**: madrac-subs  
**Status**: IMPLEMENTED but underdocumented  
**Impact**: Community features work but upgrade/merge conflict resolution unclear

**Gaps**:
- How do users upgrade to newer version of same subtitle?
- SRT versioning strategy (version bump on each edit?)
- Upload conflict resolution (if two users edit simultaneously)
- Metadata (upvotes, downvotes) — stored but never displayed

**Related**:
- CONTEXTO_COMPLETO_PARA_IA.md section 3.2–3.7 documents this
- Tests exist but coverage may be incomplete

**Owner**: madrac-subs maintainer  
**Estimated Effort**: 4–6 hours (feature completion)  
**Blocker**: No (Phase 0 accepted partial state)

---

## Low Priority (Technical Debt)

### Issue DT-006: Logging Inconsistency

**Severity**: LOW  
**Component**: All  
**Status**: KNOWN  
**Impact**: Logs are helpful for debugging but format varies

**Examples**:
- madrac-dubs uses structured logging (timestamps, function names)
- madrac-subs uses mixed logging (some structured, some printf-style)
- madrac-hub has minimal logging

**Owner**: TBD  
**Estimated Effort**: 2–3 hours (standardize)  
**Blocker**: No

---

### Issue DT-007: Error Message Localization

**Severity**: LOW  
**Component**: madrac-subs, madrac-dubs  
**Status**: PARTIAL (some strings translated)  
**Impact**: Spanish UI with English error messages (jarring UX)

**Owner**: TBD  
**Estimated Effort**: 3–4 hours (translate error strings)  
**Blocker**: No

---

### Issue DT-008: Test Coverage Analysis

**Severity**: LOW  
**Component**: All  
**Status**: UNKNOWN (no coverage metrics)  
**Impact**: Don't know which code paths are untested

**Action**:
1. Add `pytest-cov` to test setup
2. Run coverage report: `pytest --cov=src/`
3. Identify untested modules (target >80% coverage)
4. Add tests for high-risk code paths

**Owner**: TBD  
**Estimated Effort**: 2–3 hours (setup + initial report)  
**Blocker**: No

---

## Priority Matrix

| Issue | Severity | Blocker | Phase | Status |
|-------|----------|---------|-------|--------|
| DT-001 | HIGH | No | 2 | Investigation needed |
| DT-002 | MEDIUM | No | 2 | Pending (Opción A) |
| DT-003 | MEDIUM | No | 2 | Investigation needed |
| DT-004 | MEDIUM | No | 2 | Planning |
| DT-005 | MEDIUM | No | 2 | Underdocumented |
| DT-006 | LOW | No | 3 | Documentation |
| DT-007 | LOW | No | 3 | Localization |
| DT-008 | LOW | No | 3 | Metrics |

---

## Next Actions

**Immediate** (this week):
- [ ] Profile DT-001 (Demucs performance)
- [ ] Implement DT-002 (PyInstaller fix) once DT-001 stabilizes

**Soon** (next 2 weeks):
- [ ] Investigate DT-003 (cache validation)
- [ ] Document DT-004 (LLAVE system)
- [ ] Complete DT-005 (community features)

**Later** (backlog):
- [ ] DT-006, DT-007, DT-008 (polish)

---

## Assumptions & Risks

**Assumption**: Users can live with DSP mode while Demucs optimization is pending
- **Risk**: If Demucs is "always broken", users will abandon high-quality option
- **Mitigation**: Monitor actual usage; prioritize DT-001 if users complain

**Assumption**: PyInstaller fix (DT-002) can wait until Demucs is optimized
- **Risk**: If frozen .exe is the primary distribution, users stuck with DSP
- **Mitigation**: Clear documentation that `--dubs-python` is recommended for development

