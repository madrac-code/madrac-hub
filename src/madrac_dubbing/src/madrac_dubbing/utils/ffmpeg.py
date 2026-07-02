"""FFmpeg wrapper utilities — consolidated via shared madrac.utils.ffmpeg"""
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger("madrac.dubbing.ffmpeg")

try:
    from madrac.utils.ffmpeg import (
        resolve_executable,
        cancel_ffmpeg,
        get_duration as get_video_duration,
        detect_subtitle_tracks,
        pick_best_track,
        obtener_metadata_video,
        extract_subtitle_track,
    )
except ImportError:
    resolve_executable = None
    get_video_duration = None
    detect_subtitle_tracks = None
    pick_best_track = None
    obtener_metadata_video = None
    extract_subtitle_track = None

    def resolve_executable(name: str) -> Optional[str]:
        import shutil, sys
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            p = Path(sys._MEIPASS) / name
            if p.exists():
                return str(p)
        return shutil.which(name)


def extract_audio(video_path: Path, output_wav: Path) -> Path:
    """Extract audio from video (delegates to shared wrapper if available)."""
    try:
        from madrac.utils.ffmpeg import extract_audio as _extract
        _extract(str(video_path), str(output_wav))
        return output_wav
    except ImportError:
        pass
    logger.info("Extracting audio from %s", video_path)
    ffmpeg = resolve_executable("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")
    cmd = [ffmpeg, '-i', str(video_path), '-q:a', '9', '-n', str(output_wav)]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return output_wav
    except subprocess.CalledProcessError as e:
        logger.error("FFmpeg audio extraction failed: %s", e.stderr)
        raise


def get_audio_info(audio_path: Path) -> dict:
    """Get audio metadata using ffprobe."""
    ffprobe = resolve_executable("ffprobe")
    if not ffprobe:
        return {}
    cmd = [ffprobe, '-v', 'error', '-show_streams', '-of', 'json', str(audio_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logger.error("FFprobe failed: %s", e)
        return {}


def mux_audio_to_video(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    codec: str = "aac"
) -> Path:
    """Mux audio into video using ffmpeg."""
    logger.info("Muxing audio into video: %s", output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = resolve_executable("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")
    cmd = [
        ffmpeg, '-i', str(video_path), '-i', str(audio_path),
        '-c:v', 'copy', '-c:a', codec,
        '-map', '0:v:0', '-map', '1:a:0',
        '-y', str(output_path),
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info("Video muxed to %s", output_path)
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error("FFmpeg muxing failed: %s", e.stderr)
        raise
