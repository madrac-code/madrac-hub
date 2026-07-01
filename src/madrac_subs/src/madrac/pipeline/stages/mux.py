"""Mux stage: embed subtitle track into video via ffmpeg."""

from pathlib import Path
from typing import Any, Callable, Dict

from .base import PipelineStage, StageResult
from ...core import get_logger
from ...config import get_config
from ...utils.media import mux_subtitles, lang_639_2b

logger = get_logger("stage.mux")


class MuxStage(PipelineStage):
    """Embed generated subtitles into the original video file.

    Reads context["subtitle_path"] (SRT output from FormatStage)
    and context["ruta"] (original video). Writes muxed file and
    sets context["muxed_path"].
    """

    name = "mux"

    def execute(
        self,
        item_id: str,
        context: Dict[str, Any],
        on_progress: Callable,
        on_log: Callable,
        should_cancel: Callable[[], bool],
    ) -> StageResult:
        # TODO: add config checkbox "mux.auto" to auto-mux companion subtitles
        # when present (detected by _on_add_files/_detect_subtitles_for_entry
        # and stored in entry.metadata["sub_info"]["companion"])
        if not get_config("mux.habilitado", False):
            on_log("Mux disabled")
            return StageResult(True, data={"muxed": False})

        subtitle_path = context.get("subtitle_path") or context.get("output_path")
        if not subtitle_path:
            return StageResult(False, error="No subtitle path in context")

        video_path = context.get("ruta")
        if not video_path:
            return StageResult(False, error="No video path in context")

        video = Path(video_path)
        if not video.exists():
            return StageResult(False, error=f"Video not found: {video_path}")

        srt = Path(subtitle_path)
        if not srt.exists():
            return StageResult(False, error=f"Subtitle not found: {subtitle_path}")

        lang_code = get_config("traduccion.idioma_destino", "es")
        idioma = lang_639_2b(lang_code)

        try:
            on_log(f"Muxing subtitles into {video.name}...")
            on_progress(item_id, 99.0, "Muxing...")

            muxed = mux_subtitles(
                str(video), str(srt),
                language=idioma,
            )

            context["muxed_path"] = muxed
            on_log(f"[OK] Muxed: {Path(muxed).name}")
            return StageResult(True, data={
                "muxed": True,
                "muxed_path": muxed,
            })

        except Exception as e:
            logger.exception("Mux failed: %s", e)
            return StageResult(False, error=f"Mux failed: {e}")

    def rollback(self, context: Dict[str, Any]) -> None:
        muxed = context.get("muxed_path")
        ruta = context.get("ruta")
        if muxed and muxed != ruta and Path(muxed).exists():
            try:
                Path(muxed).unlink()
                logger.debug("Rollback: removed muxed %s", muxed)
            except Exception as e:
                logger.warning("Rollback mux failed: %s", e)
