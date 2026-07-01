"""MADRAC-SUBS v3 bootstrap for PyInstaller (onefile/onedir).
Sequence:
1. Set env vars (OMP/MKL threads) — before any import
2. Preload torch DLLs (frozen) — avoids C++ abort in torch_python.dll
3. import torch + torch.set_num_threads(1) — BEFORE PySide6
4. Import and run V3 app
"""

import os
import sys
import ctypes
from pathlib import Path

# ── 1. Environment variables ────────────────────────────────
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

# ── 2. Preload torch DLLs (frozen) ──────────────────────────
_es_frozen = getattr(sys, "frozen", False)
if _es_frozen and hasattr(sys, "_MEIPASS"):
    base = Path(sys._MEIPASS)
    # Add torch/lib to DLL search path
    if hasattr(os, "add_dll_directory"):
        for d in [base / "torch" / "lib", base / "_internal" / "torch" / "lib"]:
            if d.exists():
                os.add_dll_directory(str(d))
    # Preload c10.dll early
    for ruta in [
        base / "torch" / "lib" / "c10.dll",
        base / "_internal" / "torch" / "lib" / "c10.dll",
    ]:
        if ruta.exists():
            try:
                ctypes.CDLL(str(ruta))
            except OSError:
                pass
            break

# ── 3. Import torch BEFORE PySide6 ──────────────────────────
import torch
torch.set_num_threads(1)

# ── 4. Add src/ to path for V3 package ─────────────────────
sys.path.insert(0, str(Path(__file__).parent / "src"))

# ── CLI commands (--test-imports, --validate-build) ─────────
if "--test-imports" in sys.argv:
    print("[TEST] Starting frozen import tests...")
    print("[TEST] 1/2: import ctranslate2...", end=" ", flush=True)
    import ctranslate2
    print(f"OK (v{ctranslate2.__version__})")

    print("[TEST] 2/2: import faster_whisper...", end=" ", flush=True)
    import faster_whisper
    print("OK")

    print("[TEST] All import tests PASSED.")
    sys.exit(0)

if "--validate-build" in sys.argv:
    ERRORS = 0
    def check(label, ok, detail=""):
        global ERRORS
        status = "PASS" if ok else "FAIL"
        if not ok:
            ERRORS += 1
        print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))

    print("\n[validate-build] Mux stage & media utils")
    from madrac.pipeline import MuxStage as MuxFromPipeline
    from madrac.utils import mux_subtitles, demux_subtitles, probe_media
    from madrac.utils.media import lang_639_2b, detect_subtitles, strip_subtitles
    check("MuxStage from pipeline.__init__", callable(MuxFromPipeline))
    check("mux_subtitles from utils.__init__", callable(mux_subtitles))
    check("demux_subtitles from utils.__init__", callable(demux_subtitles))
    check("probe_media from utils.__init__", callable(probe_media))
    check("lang_639_2b", lang_639_2b("es") == "spa")
    check("detect_subtitles", callable(detect_subtitles))
    check("strip_subtitles", callable(strip_subtitles))

    print("\n[validate-build] Pipeline stage classes")
    from madrac.pipeline.stages import (
        AudioExtractionStage, TranscribeStage,
        TranslateStage, FormatStage, CommunityStage, MuxStage,
    )
    check("AudioExtractionStage", callable(AudioExtractionStage))
    check("TranscribeStage", callable(TranscribeStage))
    check("TranslateStage", callable(TranslateStage))
    check("FormatStage", callable(FormatStage))
    check("CommunityStage", callable(CommunityStage))
    check("MuxStage", callable(MuxStage))

    print(f"\n  Results: {ERRORS} FAILURES, all other checks PASS\n")
    sys.exit(ERRORS)

# ── 5. Launch V3 app ────────────────────────────────────────
from madrac.cli.main import main
main()
