"""Headless --fast-mux CLI for Windows Shell integration.

Usage (via registry):
    python -m madrac --fast-mux "video.mp4" "sub.srt"
    python -m madrac --fast-mux "video.mp4"          # auto-discover sibling .srt
    python -m madrac --fast-mux "sub.srt"             # auto-discover sibling video
"""

import sys
from pathlib import Path

import send2trash
from ..utils.media import mux_subtitles, lang_639_2b

_VIDEO_EXTS = [".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".wmv", ".flv"]
_SRT_EXTS = [".srt", ".ass", ".vtt"]


def _show_toast(title: str, message: str) -> None:
    """Show a Windows system tray toast if Qt is available."""
    try:
        from PySide6.QtWidgets import QSystemTrayIcon, QApplication
        from PySide6.QtGui import QIcon
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        tray = QSystemTrayIcon(app)
        icon = QIcon.fromTheme("applications-multimedia")
        if icon.isNull():
            icon = app.style().standardIcon(app.style().StandardPixmap.SP_ComputerIcon)
        tray.setIcon(icon)
        tray.show()
        tray.showMessage(title, message, QSystemTrayIcon.Information, 3000)
    except Exception:
        pass


def cli_fast_mux(argv: list) -> None:
    """Fast mux: auto-discover video/srt from single argument, or explicit pair."""
    if not argv:
        print("Usage: madrac-subs.exe --fast-mux <video.mp4> [<srt.srt>...]", file=sys.stderr)
        sys.exit(1)

    # --no-trash is added by shell verb / SendTo (not by COM DropHandler),
    # so its ABSENCE means this was triggered by Explorer drag-and-drop.
    trash_srt = '--no-trash' not in argv
    argv = [a for a in argv if a != '--no-trash']

    video_path = None
    srt_files = []

    for a in argv:
        p = Path(a).resolve()
        if not p.exists():
            continue
        if p.suffix.lower() in _VIDEO_EXTS:
            video_path = p
        elif p.suffix.lower() in _SRT_EXTS:
            srt_files.append(p)

    # Auto-discover video if only SRT was given (SendTo use case)
    if video_path is None and srt_files:
        stem = srt_files[0].stem
        for vext in _VIDEO_EXTS:
            candidate = srt_files[0].with_suffix(vext)
            if candidate.exists():
                video_path = candidate
                break
        # Also try stripping language suffixes: video.es.srt -> video.mkv
        if video_path is None and '_' in stem:
            base = stem.rsplit('_', 1)[0]
            for vext in _VIDEO_EXTS:
                candidate = srt_files[0].with_name(base + vext)
                if candidate.exists():
                    video_path = candidate
                    break

    # Auto-discover SRT if only video was given
    if video_path is not None and not srt_files:
        stem = video_path.stem
        for sext in _SRT_EXTS:
            candidate = video_path.with_suffix(sext)
            if candidate.exists():
                srt_files.append(candidate)
                break

    if video_path is None or not srt_files:
        print("Usage: madrac-subs.exe --fast-mux <video.mp4> [<srt.srt>...]", file=sys.stderr)
        sys.exit(1)

    _show_toast("MADRAC-SUBS", f"Muxeando subtítulo en {video_path.name}...")

    success_count = 0
    idioma = lang_639_2b("es")
    for srt_path in srt_files:
        try:
            result = mux_subtitles(str(video_path), str(srt_path), language=idioma)
            if trash_srt:
                send2trash.send2trash(str(srt_path.resolve()))
            print(f"[OK] Muxed: {video_path.name} + {srt_path.name} -> {Path(result).name}")
            success_count += 1
        except Exception as e:
            print(f"[ERR] {video_path.name} + {srt_path.name}: {e}", file=sys.stderr)

    if success_count > 0:
        _show_toast("MADRAC-SUBS",
            f"¡Muxeo completado! {success_count} subtítulo(s) en {video_path.name}")
    else:
        _show_toast("MADRAC-SUBS", "Error al muxear subtítulos")

    sys.exit(0 if success_count > 0 else 1)
