"""Main CLI entry point for MADRAC-SUBS v3.

Usage:
    python -m madrac          # Launch GUI
    python -m madrac transcribe file.mp4  # Headless transcription
    python -m madrac mux video.mp4 subs.srt  # Mux subtitles
"""

import sys
from ..app import main as gui_main


def main() -> None:
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--test-imports":
            _test_imports()
        elif cmd == "--test-whisper":
            _test_whisper()
        elif cmd == "--fast-mux":
            from .fast_mux import cli_fast_mux
            cli_fast_mux(sys.argv[2:])
        elif cmd == "transcribe":
            from .transcribe import cli_transcribe
            cli_transcribe(sys.argv[2:])
        elif cmd == "mux":
            from .mux import cli_mux
            cli_mux(sys.argv[2:])
        else:
            print(f"Unknown command: {cmd}", file=sys.stderr)
            sys.exit(1)
    else:
        gui_main()


def _test_imports() -> None:
    print("[TEST] Starting frozen import tests...")
    print("[TEST] 1/2: import ctranslate2...", end=" ", flush=True)
    import ctranslate2
    print(f"OK (v{ctranslate2.__version__})")
    print("[TEST] 2/2: import faster_whisper...", end=" ", flush=True)
    import faster_whisper
    print("OK")
    print("[TEST] All import tests PASSED.")
    sys.exit(0)


def _test_whisper() -> None:
    import time
    from faster_whisper import WhisperModel
    audio = sys.argv[2] if len(sys.argv) > 2 else r"D:\madracsubs\test_whisper.wav"
    print(f"[TEST] Loading Whisper tiny model...", flush=True)
    t0 = time.time()
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    t1 = time.time()
    print(f"[TEST] Model loaded in {t1-t0:.2f}s", flush=True)
    print(f"[TEST] Transcribing {audio}...", flush=True)
    segments, info = model.transcribe(audio, beam_size=1)
    t2 = time.time()
    print(f"[TEST] Transcribe took {t2-t1:.2f}s", flush=True)
    print(f"[TEST] Language: {info.language} ({info.language_probability:.2f})", flush=True)
    for seg in segments:
        print(f"  [{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text}", flush=True)
    print("[TEST] Whisper test PASSED.", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
