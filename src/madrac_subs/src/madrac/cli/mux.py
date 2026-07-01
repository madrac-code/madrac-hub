"""CLI mux command: python -m madrac mux <video> <srt> [--lang <code>]"""

import sys
from pathlib import Path

from ..utils.media import mux_subtitles, lang_639_2b


def cli_mux(argv: list) -> None:
    if len(argv) < 2:
        print("Usage: python -m madrac mux <video.mp4> <subs.srt> [--lang es]")
        sys.exit(1)

    video = argv[0]
    srt = argv[1]
    lang = "spa"
    if "--lang" in argv:
        idx = argv.index("--lang")
        if idx + 1 < len(argv):
            lang = lang_639_2b(argv[idx + 1])

    try:
        result = mux_subtitles(video, srt, language=lang)
        print(f"[OK] Muxed: {result}")
    except Exception as e:
        print(f"[ERR] {e}", file=sys.stderr)
        sys.exit(1)
