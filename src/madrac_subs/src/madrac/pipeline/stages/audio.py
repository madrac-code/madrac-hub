"""Audio extraction and validation stage."""

import time
from pathlib import Path
from subprocess import Popen, DEVNULL, PIPE, TimeoutExpired
from typing import Any, Callable, Dict, List, Optional

from .base import PipelineStage, StageResult
from ...core import get_logger
from ...config import get_config
from ...utils.ffmpeg import (
    resolve_executable,
    get_duration,
    extract_audio as _extract_audio_util,
    detect_subtitle_tracks,
    pick_best_track,
    extract_subtitle_track,
    cancel_ffmpeg,
)

logger = get_logger("stage.audio")

EXTENSIONES_VIDEO = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v", ".wmv",
    ".3gp", ".3g2", ".mts", ".ts", ".vob",
}
EXTENSIONES_AUDIO = {
    ".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma", ".opus",
}
EXTENSIONES_MULTIMEDIA = EXTENSIONES_VIDEO | EXTENSIONES_AUDIO

_POLL_INTERVAL_S = 0.5


class AudioExtractionStage(PipelineStage):
    """Validate media file and extract audio for transcription."""

    name = "audio"

    def execute(
        self,
        item_id: str,
        context: Dict[str, Any],
        on_progress: Callable,
        on_log: Callable,
        should_cancel: Callable[[], bool],
    ) -> StageResult:
        from ...core.paths import get_temp_dir

        ruta = context.get("ruta", "")
        if not ruta:
            return StageResult(False, error="No file path in context")

        path = Path(ruta)
        if not path.exists():
            return StageResult(False, error=f"File not found: {ruta}")
        if not path.is_file():
            return StageResult(False, error=f"Not a file: {ruta}")
        if path.stat().st_size < 100:
            return StageResult(False, error=f"File too small (possible corruption): {ruta}")

        ext = path.suffix.lower()
        if ext not in EXTENSIONES_MULTIMEDIA:
            return StageResult(False, error=f"Unsupported format: {ext}")

        duration = get_duration(ruta)
        context["duration_s"] = duration

        es_video = ext in EXTENSIONES_VIDEO
        audio_path = ruta
        temp_dir = get_temp_dir()

        if es_video and get_config("procesamiento.preferir_subtitulos_embebidos", True):
            pistas = detect_subtitle_tracks(ruta)
            if pistas:
                best = pick_best_track(pistas)
                if best:
                    on_log(f"Embedded subtitle detected: {best.get('language', 'unknown')}")
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    srt_out = str(temp_dir / f"{path.stem}_embedded.srt")
                    if extract_subtitle_track(ruta, best["index"], srt_out):
                        context["embedded_subs_path"] = srt_out
                        context["embedded_subs_lang"] = best.get("language", "und")
                        on_log("Using embedded subtitles - skipping audio extraction")
                        on_progress(item_id, 70.0, "Embedded subs extracted")
                        context["audio_path"] = audio_path
                        context["is_video"] = es_video
                        context["file_name"] = path.name
                        context["file_stem"] = path.stem
                        context["file_ext"] = ext
                        return StageResult(True, data={
                            "audio_path": audio_path,
                            "duration_s": duration,
                            "is_video": es_video,
                            "embedded": True,
                        })

        if es_video:
            temp_dir.mkdir(parents=True, exist_ok=True)
            audio_path = str(temp_dir / f"{path.stem}_temp_audio.wav")
            on_log(f"Extracting audio: {path.name}")
            ok = self._extract_audio_with_cancel(ruta, audio_path, should_cancel)
            if not ok:
                if should_cancel():
                    return StageResult(False, error="Cancelled during audio extraction")
                return StageResult(False, error="Audio extraction failed")
            on_progress(item_id, 15.0, "Audio extracted")

        context["audio_path"] = audio_path
        context["is_video"] = es_video
        context["file_name"] = path.name
        context["file_stem"] = path.stem
        context["file_ext"] = ext

        return StageResult(True, data={
            "audio_path": audio_path,
            "duration_s": duration,
            "is_video": es_video,
        })

    def rollback(self, context: Dict[str, Any]) -> None:
        audio = context.get("audio_path")
        if audio and context.get("is_video") and Path(audio).exists():
            try:
                Path(audio).unlink()
            except Exception:
                pass
        embedded = context.get("embedded_subs_path")
        if embedded and Path(embedded).exists():
            try:
                Path(embedded).unlink()
            except Exception:
                pass

    @staticmethod
    def _extract_audio_with_cancel(
        video_path: str, output_path: str,
        should_cancel: Callable[[], bool],
    ) -> bool:
        """Extract audio with cancellation support via polling."""
        ffmpeg = resolve_executable("ffmpeg")
        if not ffmpeg:
            return False

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            ffmpeg, "-i", video_path, "-vn",
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-y", output_path,
        ]
        CREATION_FLAGS = 0x08000000 if __import__("os").name == "nt" else 0

        try:
            proc = Popen(
                cmd, stdout=DEVNULL, stderr=PIPE,
                text=True, creationflags=CREATION_FLAGS,
            )
            # Poll loop instead of blocking communicate
            while proc.poll() is None:
                if should_cancel():
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except TimeoutExpired:
                        proc.kill()
                    cancel_ffmpeg()
                    return False
                time.sleep(_POLL_INTERVAL_S)

            if proc.returncode != 0:
                _, stderr = proc.communicate()
                logger.warning("ffmpeg error: %s", stderr[:300] if stderr else "?")
                return False
            return Path(output_path).exists()

        except Exception as e:
            cancel_ffmpeg()
            logger.warning("Audio extraction error: %s", e)
            return False
