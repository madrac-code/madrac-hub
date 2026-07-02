from pathlib import Path
import os
import shutil
import sys


def get_app_dir() -> Path:
    """
    Devuelve la carpeta donde está el exe.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent

    return Path(__file__).resolve().parents[3]


APP_DIR = get_app_dir()

MADRAC_SUBS_EXE = APP_DIR / "madrac-subs.exe"

# Buscar ffmpeg/ffprobe: primero en PATH (Linux/AppImage), luego .exe (Windows)
_ffmpeg_candidate = shutil.which("ffmpeg")
if _ffmpeg_candidate:
    FFMPEG_EXE = Path(_ffmpeg_candidate)
else:
    FFMPEG_EXE = APP_DIR / "ffmpeg.exe"

_ffprobe_candidate = shutil.which("ffprobe")
if _ffprobe_candidate:
    FFPROBE_EXE = Path(_ffprobe_candidate)
else:
    FFPROBE_EXE = APP_DIR / "ffprobe.exe"