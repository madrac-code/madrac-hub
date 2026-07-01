"""FFmpeg/FFprobe executable resolution and wrappers."""

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.logging import get_logger

logger = get_logger("utils.ffmpeg")

_ffmpeg_lock = threading.Lock()
_ffmpeg_active: Optional[subprocess.Popen] = None

CREATION_FLAGS = 0x08000000 if os.name == "nt" else 0


def resolve_executable(name: str) -> Optional[str]:
    """Find ffmpeg/ffprobe in PyInstaller bundle or PATH."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        p = Path(sys._MEIPASS) / name
        if p.exists():
            return str(p)
    found = shutil.which(name)
    return found


def cancel_ffmpeg() -> None:
    """Terminate active ffmpeg process."""
    global _ffmpeg_active
    with _ffmpeg_lock:
        proc = _ffmpeg_active
        _ffmpeg_active = None
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    except Exception as e:
        logger.warning("Error cancelling ffmpeg: %s", e)


def get_duration(file_path: str) -> float:
    """Get media duration in seconds via ffprobe."""
    ffprobe = resolve_executable("ffprobe")
    if not ffprobe:
        return 0.0
    try:
        r = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            capture_output=True, text=True, timeout=10,
            creationflags=CREATION_FLAGS,
        )
        if r.returncode == 0:
            return float(r.stdout.strip())
    except Exception:
        pass
    return 0.0


def extract_audio(video_path: str, output_path: str) -> bool:
    """Extract 16kHz mono WAV audio from video file."""
    global _ffmpeg_active
    ffmpeg = resolve_executable("ffmpeg")
    if not ffmpeg:
        return False
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-i", video_path, "-vn",
        "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-y", output_path,
    ]
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            text=True, creationflags=CREATION_FLAGS,
        )
        _, stderr = proc.communicate(timeout=3600)
        if proc.returncode != 0:
            logger.warning("ffmpeg error: %s", stderr[:300])
            return False
        return Path(output_path).exists()
    except subprocess.TimeoutExpired:
        cancel_ffmpeg()
        return False
    except Exception as e:
        cancel_ffmpeg()
        logger.warning("Audio extraction error: %s", e)
        return False


_SKIP_TITLE_WORDS = {"sign", "song", "music", "karaoke", "opening", "ending", "credit"}


def detect_subtitle_tracks(video_path: str) -> List[Dict[str, Any]]:
    """List embedded subtitle streams via ffprobe (with packet count and title)."""
    ffprobe = resolve_executable("ffprobe")
    if not ffprobe:
        logger.warning("ffprobe not found in PATH or bundle")
        return []
    try:
        import json
        r = subprocess.run(
            [ffprobe, "-v", "error", "-count_packets",
             "-select_streams", "s",
             "-show_entries",
             "stream=index,codec_name,nb_read_packets:stream_tags=language,title",
             "-of", "json", video_path],
            capture_output=True, text=True, timeout=15,
            creationflags=CREATION_FLAGS,
        )
        if r.returncode != 0:
            logger.warning("ffprobe error detecting subtitles: %s", r.stderr[:200])
            return []
        data = json.loads(r.stdout)
        tracks = []
        for s in data.get("streams", []):
            tags = s.get("tags") or {}
            tracks.append({
                "index": s["index"],
                "codec": s.get("codec_name", "?"),
                "language": tags.get("language", "und"),
                "title": tags.get("title", ""),
                "packets": int(s.get("nb_read_packets", 0)),
            })
        return tracks
    except json.JSONDecodeError as e:
        logger.warning("Error parsing subtitle track info: %s", e)
        return []
    except subprocess.TimeoutExpired:
        logger.warning("Timeout detecting subtitle tracks")
        return []
    except Exception as e:
        logger.warning("Unexpected error detecting subtitle tracks: %s", e)
        return []


_LANG_PRIORITY = {"spa": 0, "eng": 1}


def pick_best_track(tracks: List[Dict]) -> Optional[Dict]:
    """Select best subtitle track: prefer dialogue tracks over signs/songs/music."""
    if not tracks:
        return None

    def _key(t: Dict) -> tuple:
        title = (t.get("title") or "").lower()
        lang = t.get("language", "und")
        packets = t.get("packets", 0)

        has_skip = any(w in title for w in _SKIP_TITLE_WORDS)
        lang_priority = 1000 + _LANG_PRIORITY.get(lang, 999) if has_skip else _LANG_PRIORITY.get(lang, 999)

        return (lang_priority, -packets)

    return min(tracks, key=_key)


def obtener_metadata_video(ruta: str) -> Dict[str, Any]:
    """Extrae metadata real del video via ffprobe (JSON)."""
    ffprobe = resolve_executable("ffprobe")
    if not ffprobe:
        return {}
    try:
        import json
        r = subprocess.run(
            [ffprobe, "-v", "error",
             "-show_entries",
             "stream=index,codec_name,codec_type,width,height,r_frame_rate,bit_rate:"
             "format=format_name,duration,bit_rate",
             "-of", "json", ruta],
            capture_output=True, text=True, timeout=30,
            creationflags=CREATION_FLAGS,
        )
        if r.returncode != 0:
            logger.warning("ffprobe error for %s: %s", ruta, r.stderr[:200])
            return {}
        data = json.loads(r.stdout)
        streams = data.get("streams", [])
        fmt = data.get("format", {})

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

        fps = 0.0
        if video_stream:
            fr = video_stream.get("r_frame_rate", "")
            if "/" in fr:
                try:
                    num, den = fr.split("/")
                    fps = round(float(num) / float(den), 3) if float(den) > 0 else 0.0
                except (ValueError, ZeroDivisionError):
                    pass

        bitrate = fmt.get("bit_rate")
        if bitrate:
            bitrate = int(bitrate) // 1000  # convert to kbps

        return {
            "width": video_stream.get("width") if video_stream else None,
            "height": video_stream.get("height") if video_stream else None,
            "fps": fps,
            "bitrate": bitrate,
            "video_codec": video_stream.get("codec_name") if video_stream else None,
            "audio_codec": audio_streams[0].get("codec_name") if audio_streams else None,
            "audio_tracks": len(audio_streams),
            "container": fmt.get("format_name"),
            "duration_sec": float(fmt["duration"]) if fmt.get("duration") else 0.0,
        }
    except json.JSONDecodeError:
        logger.warning("ffprobe JSON parse error for %s", ruta)
    except subprocess.TimeoutExpired:
        logger.warning("ffprobe timeout for %s", ruta)
    except Exception as e:
        logger.warning("ffprobe metadata error: %s", e)
    return {}


def extract_subtitle_track(video_path: str, stream_index: int, output_path: str) -> bool:
    """Extract a subtitle track as SRT."""
    ffmpeg = resolve_executable("ffmpeg")
    if not ffmpeg:
        logger.warning("ffmpeg not found — cannot extract subtitle track")
        return False
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-i", video_path, "-map", f"0:{stream_index}",
        "-c:s", "srt", "-y", output_path,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                           creationflags=CREATION_FLAGS)
        if r.returncode != 0:
            logger.warning("Subtitle extraction failed (stream %d): %s",
                           stream_index, r.stderr[:500])
            return False
        return Path(output_path).exists()
    except Exception as e:
        logger.warning("Subtitle extraction error: %s", e)
        return False
