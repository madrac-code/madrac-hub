"""Community features stage — uses real CLIENTE singleton."""

from pathlib import Path
from typing import Any, Callable, Dict

from .base import PipelineStage, StageResult
from ...core import get_logger, get_bus as get_event_bus, read_text
from ...core.parser import parse_video_filename
from ...config import get_config
from ...supabase_client import CLIENTE
from ...utils import sha256 as compute_sha256
from ...utils.ffmpeg import obtener_metadata_video

logger = get_logger("stage.community")


def _word_count(content: str) -> int:
    return sum(len(line.split()) for line in content.splitlines()
               if line.strip() and not line.strip().isdigit()
               and "-->" not in line)


def _derive_resolution(width=None, height=None, fallback=None):
    """Derive resolution label from actual pixel dimensions."""
    if width and height:
        if width >= 3840 or height >= 2160:
            return "2160p"
        if width >= 1920 or height >= 1080:
            return "1080p"
        if width >= 1280 or height >= 720:
            return "720p"
        if width >= 854 or height >= 480:
            return "480p"
        if width >= 640 or height >= 360:
            return "360p"
    return fallback


class CommunityStage(PipelineStage):
    """Check / upload community subtitles via Supabase (feature-flagged)."""

    name = "community"

    def execute(
        self,
        item_id: str,
        context: Dict[str, Any],
        on_progress: Callable,
        on_log: Callable,
        should_cancel: Callable[[], bool],
    ) -> StageResult:
        if not get_config("comunidad.habilitado", False):
            return StageResult(True, data={"used_community": False})

        bus = get_event_bus()
        ruta = context.get("ruta", "")
        file_stem = context.get("file_stem", Path(ruta).stem)
        output_path = context.get("output_path", "")
        subtitle_path = context.get("subtitle_path", output_path)

        subs_path = Path(subtitle_path) if subtitle_path else None
        if not subs_path or not subs_path.exists():
            on_log("[SKIP] No subtitle file to check")
            return StageResult(True, data={"used_community": False})

        try:
            # ── Level 1: ffprobe — always when video file exists ──
            media_info: Dict[str, Any] = {}
            if ruta:
                on_log("Extrayendo metadatos del video...")
                media_info = obtener_metadata_video(ruta)

            # ── Level 2: Parser — only if normalization enabled ──
            normalizacion_habilitada = get_config("comunidad.normalizacion_habilitada", True)
            parsed: Dict[str, Any] = {}
            if normalizacion_habilitada and ruta:
                on_log("Analizando nombre del archivo...")
                parsed = parse_video_filename(file_stem)

            # Derive resolution from actual dimensions (overrides parser guess)
            derived_resolution = _derive_resolution(
                width=media_info.get("width"),
                height=media_info.get("height"),
                fallback=parsed.get("resolution") if normalizacion_habilitada else None,
            )

            file_hash = context.get("video_hash") or compute_sha256(subs_path)
            if not file_hash:
                on_log("[WARN] Could not compute hash")
                return StageResult(True, data={"used_community": False})

            # ── Search (always, even without normalization) ──
            on_log("Checking community subtitles...")
            idioma_busqueda = get_config("traduccion.idioma_destino", "es")
            duracion_seg = context.get("duration_s", 0.0)
            resultados = CLIENTE.buscar_por_hash(
                file_hash, idioma=idioma_busqueda,
                duracion_seg=duracion_seg, tolerancia_seg=3.0,
            )
            if resultados:
                filename = resultados[0].get("filename", "")
                if filename:
                    url = f"{CLIENTE._storage_url}{filename}"
                    on_log("[INFO] Subtitle available on community")
                    return StageResult(True, data={
                        "used_community": False,
                        "available": True,
                        "url": url,
                    })

            # ── Level 3: Upload — login + consent + auto ──
            puede_subir = (
                CLIENTE.is_logged_in()
                and get_config("comunidad.share_consent_given", False)
                and get_config("comunidad.subir_automaticamente", True)
            )

            if puede_subir:
                on_log("Uploading to community...")
                contenido = read_text(subs_path)
                wc = _word_count(contenido)

                ok = CLIENTE.compartir_subtitulo(
                    ruta_srt=subs_path,
                    video_hash=file_hash,
                    video_nombre=file_stem,
                    duracion_seg=media_info.get("duration_sec", 0),
                    tamano_bytes=subs_path.stat().st_size,
                    idioma=context.get("idioma", "es"),
                    es_revision_manual=False,
                    word_count=wc,
                    avg_confidence=context.get("avg_confidence", 0.0),
                    # ffprobe metadata (always available if video exists)
                    fps=media_info.get("fps"),
                    bitrate=media_info.get("bitrate"),
                    width=media_info.get("width"),
                    height=media_info.get("height"),
                    video_codec=media_info.get("video_codec"),
                    audio_codec=media_info.get("audio_codec"),
                    container=media_info.get("container"),
                    resolution=derived_resolution,
                    # Parser metadata (only if normalization enabled)
                    season=parsed.get("season") if normalizacion_habilitada else None,
                    episode=parsed.get("episode") if normalizacion_habilitada else None,
                    year=parsed.get("year") if normalizacion_habilitada else None,
                    title_clean=parsed.get("title_clean") if normalizacion_habilitada else None,
                    release_group=parsed.get("release_group") if normalizacion_habilitada else None,
                    source_type=parsed.get("source") if normalizacion_habilitada else None,
                    parse_confidence=parsed.get("confidence") if normalizacion_habilitada else None,
                    normalization_version=parsed.get("normalization_version") if normalizacion_habilitada else None,
                )
                if ok:
                    on_log("[OK] Uploaded to community")
                    bus.emit("community.uploaded", {"path": str(subs_path)})
                else:
                    on_log("[WARN] Community upload failed")

            return StageResult(True, data={"used_community": True})

        except Exception as e:
            logger.warning("Community stage: %s", e)
            on_log(f"[WARN] Community: {e}")
            return StageResult(True, data={"used_community": False, "error": str(e)})
