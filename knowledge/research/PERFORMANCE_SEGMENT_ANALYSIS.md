# Segment-based Demucs Processing — Feasibility Analysis

**Status**: DISCARDED — not feasible  
**Date**: 2026-07-01

## Question

Can Demucs operate efficiently on extracted speech segments only (using Whisper timestamps) instead of the complete audio?

## Answer

**No.** The approach is discarded due to startup overhead.

## Why

Demucs loads a PyTorch model (~2 GB RAM) on every invocation. The model loading + GPU warmup takes ~30 seconds per execution. Processing N segments individually would require N model loads, making the total time:

```
Total ≈ N × (30s loading + processing_time_per_segment)

For a typical video with 45 segments:
45 × 30s = 22.5 min solo en carga de modelo
vs. actual: ~10 min para una ejecución completa
```

The segment-based approach would be **3–5x slower** than the current single-pass approach.

## Additional disadvantages

- **Context loss**: Demucs uses spectral context around each segment; isolated short clips produce worse separation quality
- **Background gaps**: Background audio between speech segments is lost, creating audible "cuts"
- **Synchronization complexity**: Each segment's output must be realigned to the original timeline
- **Quality degradation**: Short segments (<3s) give poor separation results

## Recommendation

Do not implement. Not an ADR — pure implementation detail, conclusively discarded.

## Estimated complexity

High (requires changes in `separation.py`, `mixer.py`, and pipeline orchestration) — not worth the negative ROI.
