# Postmortem — Torch Frozen Bug

**Date discovered**: ~2026-06-24  
**Date documented**: 2026-06-26  
**Status**: UNRESOLVED — workaround exists, root cause not fixed  
**Components affected**: SUBS, potentially ASISTENTE, DUBS

## What Happened

PyTorch freezes during model initialization when launched from a PyInstaller-packaged executable with `console=False`. The process hangs indefinitely with no error output.

## Evidence

- `TORCH_FROZEN_BUG_ANALYSIS.md` in madrac-subs
- Commits: `25fbb19` (analysis), `36408cc` (dependency pin attempt)
- Log files: `exe_stderr.log` (4 variants), `exe_stdout.log` (4 variants)

## Root Cause (hypothesis)

CTranslate2 and PyTorch use C extensions that perform multiprocessing initialization at import time. PyInstaller's frozen environment breaks the multiprocessing spawn context, causing a deadlock.

## Current Workaround

Distribute via venv + launcher .bat instead of PyInstaller. This bypasses the issue entirely.

## Required Fix (future)

Option A: Migrate to ONNX Runtime for inference (eliminates torch dependency)
Option B: Use Nuitka instead of PyInstaller (real compilation, C-ext compatible)
Option C: Implement `if __name__ == '__main__': freeze_support()` correctly and audit all multiprocessing entry points

## Lessons Learned

- Do not use PyInstaller with torch+CTranslate2 (see ADR-001)
- Freezing bugs produce no error output — add explicit timeout detection
- Test packaged executable on a clean machine before declaring rc1
