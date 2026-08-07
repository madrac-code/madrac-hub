# LLAVE-006 — tokenizers 0.15.x + Python 3.14: hard crash (0xc0000005)

**Date**: 2026-08-07
**Status**: Fixed
**Components**: MADRAC-SUBS (pipeline/transcribe), monorepo requirements

## Problem

Loading the Whisper model and calling `WhisperModel.transcribe(...)` under
Python 3.14 crashed the **entire process** with an access violation
(`0xc0000005`) in `tokenizers.cp314-win_amd64.pyd`, exit code `-1073741819`.

Symptoms observed while transcribing `test_video.mp4` via MCP:
- Whisper audio was extracted and saved (`audio_whisper.wav`), then the
  process died with no Python traceback.
- Windows Event Log (Application, Event 1000): faulting module
  `tokenizers\tokenizers.cp314-win_amd64.pyd`, offset `0x10e798`.
- Repro also happened **in the venv** (not frozen) — so it was NOT a
  PyInstaller packaging issue.

## Root Cause

`tokenizers==0.15.2` (the version resolved by `transformers>=4.35.2,<4.40.0`
which pins `tokenizers<0.19`) has a bug/wheel incompatibility with Python
3.14 on Windows. `transformers 4.39.x` enforces `tokenizers>=0.14,<0.19`,
locking in the broken wheel.

## Fix

Upgraded the pair to compatible versions:
- `tokenizers 0.15.2 -> 0.22.2`
- `transformers 4.39.3 -> 5.14.1` (still has `MarianMTModel`/`MarianTokenizer`,
  which `translator.py` and `TranslateStage` use; verified EN->ES works)

Updated pins so fresh installs never resolve the broken combo:
- `requirements.txt`: `transformers>=4.40.0,<6.0.0`, `tokenizers>=0.20.0`
- `requirements-linux.txt`: same change

Also added `tokenizers*.pyd` to the `upx_exclude` list in
`madrac-subs-v3-onefile.spec` (UPX is known to corrupt the tokenizers .pyd in
frozen builds; the file is gitignored via `*.spec`, so this is a local/packaging
change to redo in each build machine spec).

## Verification

- `faster_whisper.WhisperModel('base', cpu, int8)` transcodes the 19 MB test
  video: 5 segments, lang `es`, exit code 0.
- `transformers` imports, `AutoTokenizer` loads, MarianMT `opus-mt-en-es`
  translation produces correct output.
- Full suite: 367 passed, 6 deselected.

## Lesson

Never resolve `transformers`/`tokenizers` fresh on Python>=3.13 without
bumping the tokenizers floor to >=0.20. Check the pair version together.