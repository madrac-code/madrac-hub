"""Utility modules for MADRAC-SUBS v3.

Provides low-level reusable functions ported from the monolithic v2 utils.py.
"""

from .ffmpeg import (
    resolve_executable, cancel_ffmpeg, get_duration, extract_audio,
    detect_subtitle_tracks, pick_best_track, extract_subtitle_track,
    obtener_metadata_video,
)
from .files import (
    validate_file, normalize_path, output_dir_for, remove_temp, get_file_stem,
)
from .hashing import sha256
from .time import (
    srt_timestamp, vtt_timestamp, ass_timestamp,
    human_duration, estimate_transcription_time,
)
from .media import (
    mux_subtitles, demux_subtitles, detect_subtitles,
    strip_subtitles, lang_639_2b, probe_media,
)
from .system import (
    open_in_explorer, disk_usage_by_category,
    clean_temp, clean_logs, clean_hf_cache, clean_all,
)

__all__ = [
    # ffmpeg
    "resolve_executable", "cancel_ffmpeg", "get_duration", "extract_audio",
    "detect_subtitle_tracks", "pick_best_track", "extract_subtitle_track",
    # files
    "validate_file", "normalize_path", "output_dir_for", "remove_temp", "get_file_stem",
    # hashing
    "sha256",
    # time
    "srt_timestamp", "vtt_timestamp", "ass_timestamp",
    "human_duration", "estimate_transcription_time",
    # media
    "mux_subtitles", "demux_subtitles", "detect_subtitles",
    "strip_subtitles", "lang_639_2b", "probe_media",
    # system
    "open_in_explorer", "disk_usage_by_category",
    "clean_temp", "clean_logs", "clean_hf_cache", "clean_all",
]
