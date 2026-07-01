"""Media manipulation: mux, demux, strip subtitle streams via FFmpeg."""

import subprocess
from pathlib import Path
from subprocess import run as _srun, DEVNULL, PIPE
from typing import Dict, List, Optional

from ..core.logging import get_logger
from .ffmpeg import resolve_executable, detect_subtitle_tracks, extract_subtitle_track

logger = get_logger("utils.media")

_CONTAINER_CODEC: Dict[str, str] = {
    ".mp4":  "mov_text",
    ".m4v":  "mov_text",
    ".mkv":  "srt",
    ".webm": "webvtt",
    ".mov":  "mov_text",
    ".avi":  "srt",
}

_ISO_639_1_TO_2B: Dict[str, str] = {
    "es": "spa", "en": "eng", "pt": "por", "fr": "fra",
    "de": "deu", "it": "ita", "ja": "jpn", "zh": "zho",
    "ru": "rus", "ar": "ara", "ko": "kor", "nl": "nld",
    "pl": "pol", "sv": "swe", "da": "dan", "fi": "fin",
    "el": "ell", "he": "heb", "hi": "hin", "th": "tha",
    "tr": "tur", "vi": "vie", "cs": "ces", "ro": "ron",
    "hu": "hun", "uk": "ukr",
}

_ISO_639_2B_TO_NAME: Dict[str, str] = {
    "spa": "Español", "eng": "English", "por": "Portugués",
    "fra": "Francés", "deu": "Alemán", "ita": "Italiano",
    "jpn": "Japonés", "zho": "Chino", "rus": "Ruso",
    "ara": "Árabe", "kor": "Coreano", "nld": "Neerlandés",
    "pol": "Polaco", "swe": "Sueco", "dan": "Danés",
    "fin": "Finlandés", "ell": "Griego", "heb": "Hebreo",
    "hin": "Hindi", "tha": "Tailandés", "tur": "Turco",
    "vie": "Vietnamita", "ces": "Checo", "ron": "Rumano",
    "hun": "Húngaro", "ukr": "Ucraniano",
}

_CREATION_FLAGS = 0x08000000 if __import__("os").name == "nt" else 0


def _subtitle_codec(ext: str) -> str:
    return _CONTAINER_CODEC.get(ext.lower(), "srt")


def lang_639_2b(code: str) -> str:
    return _ISO_639_1_TO_2B.get(code, "und")


# ── Public API ──────────────────────────────────────────────────────────────


def probe_media(video_path: str) -> Dict:
    """Return a summary dict with stream counts and subtitle languages.

    Returns:
        {
            "path": str,
            "container": str (ext),
            "video_streams": int,
            "audio_streams": int,
            "subtitle_streams": int,
            "subtitle_languages": List[str],
        }
    """
    info: Dict = {
        "path": video_path,
        "container": Path(video_path).suffix.lower(),
        "video_streams": 0,
        "audio_streams": 0,
        "subtitle_streams": 0,
        "subtitle_languages": [],
    }
    ffprobe = resolve_executable("ffprobe")
    if not ffprobe or not Path(video_path).exists():
        return info

    try:
        import json
        r = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries",
             "stream=index,codec_type:stream_tags=language",
             "-of", "json", video_path],
            capture_output=True, text=True, timeout=15,
            creationflags=_CREATION_FLAGS,
        )
        if r.returncode != 0:
            return info
        data = json.loads(r.stdout)
        for s in data.get("streams", []):
            ctype = s.get("codec_type", "")
            tags = s.get("tags") or {}
            if ctype == "video":
                info["video_streams"] += 1
            elif ctype == "audio":
                info["audio_streams"] += 1
            elif ctype == "subtitle":
                info["subtitle_streams"] += 1
                info["subtitle_languages"].append(tags.get("language", "und"))
    except Exception:
        pass
    return info


def detect_subtitles(video_path: str) -> List[Dict]:
    """Detect embedded subtitle tracks in a video file."""
    return detect_subtitle_tracks(video_path)


def mux_subtitles(
    video_path: str,
    srt_path: str,
    output_path: Optional[str] = None,
    language: str = "spa",
) -> str:
    """Mux an SRT subtitle track into a video file (stream copy, no re-encode).

    Returns the path to the muxed output file.
    Raises FileNotFoundError if source files are missing.
    Raises RuntimeError on ffmpeg failure.
    """
    video = Path(video_path)
    srt = Path(srt_path)
    if not video.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not srt.exists():
        raise FileNotFoundError(f"SRT not found: {srt_path}")

    ext = video.suffix.lower()
    srt_suffix = srt.suffix.lower()

    if srt_suffix == ".ass" and ext == ".mkv":
        codec = "ass"
    else:
        codec = _subtitle_codec(ext)

    if output_path is None:
        output_path = str(video.with_name(f"{video.stem}_muxed_temp{ext}"))

    out = Path(output_path)
    if out.exists():
        out.unlink()

    ffmpeg = resolve_executable("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found in PATH or bundle")

    lang_name = _ISO_639_2B_TO_NAME.get(language, language)
    cmd = [
        ffmpeg, "-i", str(video),
        "-i", str(srt),
        "-c", "copy",
        "-c:s", codec,
        "-metadata:s:s:0", f"language={language}",
        "-metadata:s:s:0", f"title={lang_name}",
        "-map", "0:v",
        "-map", "0:a",
        "-map", "1",
        "-y",
        str(out),
    ]

    proc = _srun(cmd, capture_output=True, text=True, creationflags=_CREATION_FLAGS)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg mux failed (code {proc.returncode}): {proc.stderr[:500]}"
        )

    # Replace original video with muxed file
    if out.exists():
        video.unlink(missing_ok=True)
        out.rename(video)
    logger.info("Muxed: %s", video.name)
    return str(video)


def demux_subtitles(
    video_path: str,
    output_dir: Optional[str] = None,
) -> List[str]:
    """Extract all embedded subtitle tracks from a video as SRT files.

    Returns list of paths to extracted SRT files.
    """
    tracks = detect_subtitle_tracks(video_path)
    if not tracks:
        return []

    video = Path(video_path)
    if output_dir is None:
        output_dir = str(video.parent)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result: List[str] = []
    for t in tracks:
        lang = t.get("language", "und")
        srt_out = str(out_dir / f"{video.stem}_{lang}.srt")
        if extract_subtitle_track(video_path, t["index"], srt_out):
            result.append(srt_out)
    return result


def strip_subtitles(
    video_path: str,
    output_path: Optional[str] = None,
) -> str:
    """Remove all subtitle streams from a video (stream copy, no re-encode).

    Returns the path to the stripped output file.
    Raises FileNotFoundError if video is missing.
    Raises RuntimeError on ffmpeg failure.
    """
    video = Path(video_path)
    if not video.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    ext = video.suffix.lower()
    if output_path is None:
        output_path = str(video.with_name(f"{video.stem}_clean{ext}"))

    out = Path(output_path)
    if out.exists():
        out.unlink()

    ffmpeg = resolve_executable("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found in PATH or bundle")

    cmd = [
        ffmpeg, "-i", str(video),
        "-map", "0",
        "-map", "-0:s",
        "-c", "copy",
        "-y",
        str(out),
    ]

    proc = _srun(cmd, capture_output=True, text=True, creationflags=_CREATION_FLAGS)
    if proc.returncode != 0:
        if out.exists():
            out.unlink()
        raise RuntimeError(
            f"ffmpeg strip failed (code {proc.returncode}): {proc.stderr[:500]}"
        )

    logger.info("Stripped subtitles: %s", out.name)
    return str(out)
