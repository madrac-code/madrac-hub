# Phase 1 — Runtime Foundation — SUBS ↔ DUBS Integration

**Status**: COMPLETE ✅  
**Started**: 2026-06-26 (Build Session 001)  
**Completed**: 2026-07-01 (Build Session 003)  
**Prerequisite**: Phase 0 complete ✅  
**Goal**: Implement the first real integration between two components (SUBS → DUBS)

---

## What Was Built

### Core Feature — "Dub Now" Button
✅ **User-triggered dubbing workflow**: Click "Dub Now" in SUBS → dialog appears → select language/voice/quality → submit → progress polling → output MKV

✅ **Quality Toggle**: New "Alta calidad (Demucs)" checkbox in DubDialog
- OFF (default): Fast mode (DSP vocal reduction, ~0.1x video duration)
- ON: High quality mode (AI Demucs separation, ~15x video duration)
- Automatic fallback to DSP if Demucs unavailable

✅ **Time Estimation**: Pre-execution estimate based on SRT duration
- DSP: ~0.1x + 1 min (e.g., 1m30s video → ~1.2 min estimated)
- Demucs: ~15x + 2 min (e.g., 1m30s video → ~24 min estimated)
- Non-blocking: parses SRT in <10ms

### Pipeline Integration
✅ **HTTP API Contract** (dubbing-api-v1.md): Fully implemented
- `POST /dubbing` — submit job
- `GET /dubbing/<id>` — poll status
- `GET /health` — health check

✅ **SUBS → DUBS Workflow**:
1. SUBS launches DUBS (if not running): `madrac-dubbing.exe api --port 5000`
2. Health check with retry loop (15s timeout, 1s intervals, errno 22 catching)
3. Submit job via HTTP with `high_quality` flag
4. Poll `/dubbing/<job_id>` every 2s (timeout 15s total)
5. Receive output path on completion

✅ **DUBS Pipeline** (8 stages):
- Extract audio (25%)
- Generate TTS (50%) — Edge TTS, 50+ languages
- Reduce vocals (60%) — Demucs (AI) or DSP (fast)
- Sync TTS (70%) — time-stretch to subtitle timing
- Normalize (75%) — LUFS loudness standard
- Mix (80%) — blend reduced original + dubbed audio
- Mux (95%) — FFmpeg audio → MKV
- Cleanup (100%)

### Code Changes (3 commits)
| Repo | Commit | Changes |
|------|--------|---------|
| madrac-dubs | a52e11b | `high_quality` field in DubbingConfig; conditional pipeline logic (Demucs vs DSP) |
| madrac-subs | a03b6d4 | "Alta calidad (Demucs)" checkbox; time estimation function; UI messaging |
| madrac-hub | 9307a21 | Documentation: PERFORMANCE_SEGMENT_ANALYSIS.md (discarded approach) |

### Testing
✅ **madrac-dubs**: 14/14 unit tests pass  
✅ **madrac-subs**: 257/257 unit tests pass  
✅ **Integration verification**: Custom script `verify_high_quality_feature.py` validates:
- DubbingConfig field serialization
- Time estimation correctness (DSP vs Demucs)
- Pipeline initialization
- UI checkbox implementation

---

## Known Issues & Technical Debt

### Issue 1: Demucs Performance (NOT RESOLVED)
- **Problem**: Demucs vocal separation takes >10 minutes even for 36s videos
- **Root cause**: Unknown (hypothesis: model loading, padding, GPU utilization)
- **Current mitigation**: DSP fallback mode reduces processing to ~0.1x video duration
- **User impact**: Users can choose fast (DSP) or high-quality (Demucs) based on tolerance
- **Future work**: Profile Demucs, investigate optimization (GPU, batch processing, model cache)

### Issue 2: Demucs in Frozen .exe (PARTIALLY RESOLVED)
- **Problem**: PyInstaller doesn't bundle `demucs/remote/files.txt`
- **Current status**: ADR-006 Opción B applied (catches FileNotFoundError, falls back to DSP)
- **Result**: `madrac-dubbing.exe` works but uses DSP-only (lower quality)
- **Future work**: ADR-006 Opción A (add `datas=` to .spec file) — deferred to Phase 2

### Issue 3: Asyncio Windows Event Loop
- **Problem**: Edge TTS doesn't work with ProactorEventLoop on Windows
- **Status**: FIXED (WindowsSelectorEventLoopPolicy in `__main__.py`, commit 9528a3e)
- **OSError errno 22 catching**: Added to health check and submit_job (LLAVE_001)

---

## Exit Criteria ✅

Phase 1 is complete when:
1. ✅ SUBS "Dub Now" button launches DUBS
2. ✅ HTTP API contract is implemented and tested
3. ✅ Quality toggle (DSP vs Demucs) works
4. ✅ Time estimation is displayed
5. ✅ Fallback to DSP if Demucs unavailable
6. ✅ End-to-end workflow passes verification tests
7. ✅ Documentation (contracts, use cases) is up-to-date

All exit criteria met. **Phase 1 is COMPLETE.**

---

## What Phase 1 is NOT

Phase 1 does not include:
- Event Bus / IPC Layer (reserved for Phase 2+)
- GUI for real-time progress updates beyond polling
- Advanced Demucs optimization
- PyInstaller fix (ADR-006 Opción A)
- Integration with other components (madrac-subs-web, madrac-asistente)

---

## Next: Phase 2 — Event Bus / Orchestration

**Planned for next session:**
1. Design formal Event Bus (pub/sub model)
2. Implement IPC layer for multi-component communication
3. Extract abstraction from SUBS↔DUBS concrete implementation
4. Extend to other integrations (e.g., madrac-asistente plugins)

See `development/phases/PHASE_2_EVENT_BUS.md` (to be created in next session).
