"""Transcription stage using faster-whisper."""

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import PipelineStage, StageResult
from ...core import get_logger, get_thread_info
from ...config import get_config

logger = get_logger("stage.transcribe")


class TranscribeStage(PipelineStage):
    """Transcribe audio using faster-whisper with language detection."""

    name = "transcribe"

    def __init__(self) -> None:
        super().__init__()
        self._model: Any = None
        self._loaded = False

    def load_model(self, on_log: Callable) -> bool:
        if self._loaded:
            return True
        try:
            modelo = get_config("whisper.modelo", "base")
            device = get_config("whisper.dispositivo", "cpu")
            compute_type = get_config("whisper.compute_type", "int8")
            cpu_threads = get_config("whisper.thread_count", 0)
            if cpu_threads == 0:
                cpu_threads = get_thread_info().get("torch_threads", 4)

            on_log(f"Loading Whisper ({modelo})...")
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                modelo,
                device=device,
                compute_type=compute_type,
                cpu_threads=cpu_threads,
            )
            self._loaded = True
            on_log("[OK] Whisper loaded")
            return True
        except Exception as e:
            logger.exception("Failed to load Whisper: %s", e)
            on_log(f"[ERR] Whisper load failed: {e}")
            return False

    def execute(
        self,
        item_id: str,
        context: Dict[str, Any],
        on_progress: Callable,
        on_log: Callable,
        should_cancel: Callable[[], bool],
    ) -> StageResult:
        # ── Embedded subtitles shortcut (highest priority) ──
        embedded_path = context.get("embedded_subs_path")
        if embedded_path and Path(embedded_path).exists():
            on_log(f"Using embedded subtitles: {Path(embedded_path).name}")
            from ..stages.format import cargar_desde_srt
            try:
                subtitulos = cargar_desde_srt(embedded_path)
                if subtitulos:
                    segment_list = [
                        {"start": s.start, "end": s.end, "text": s.text}
                        for s in subtitulos
                    ]
                    lang_raw = context.get("embedded_subs_lang", "und")
                    lang_map = {"eng": "en", "spa": "es", "jpn": "ja", "zho": "zh",
                                "fra": "fr", "deu": "de", "ita": "it", "por": "pt",
                                "rus": "ru", "kor": "ko", "ara": "ar", "heb": "he",
                                "hin": "hi", "tha": "th", "vie": "vi", "und": "en"}
                    original_lang = lang_map.get(lang_raw, lang_raw)
                    on_log(f"[OK] Loaded {len(segment_list)} segments from embedded subs (lang={original_lang})")
                    on_progress(item_id, 70.0, "Embedded subs loaded")
                    context["segments"] = segment_list
                    context["original_lang"] = original_lang
                    return StageResult(True, data={
                        "segments": segment_list,
                        "original_lang": original_lang,
                        "segment_count": len(segment_list),
                    })
            except Exception as e:
                on_log(f"[WARN] Fallback to Whisper: embedded sub load failed ({e})")

        # ── Existing SRT shortcut (skip pipeline when output already exists) ──
        formato = get_config("salida.formato", "srt")
        file_stem = context.get("file_stem", "")
        if not file_stem:
            ruta = context.get("ruta", "")
            file_stem = Path(ruta).stem if ruta else "output"
        output_dir = get_config("salida.directorio", "")
        if not output_dir or not Path(output_dir).exists():
            ruta = context.get("ruta", "")
            if ruta:
                output_dir = str(Path(ruta).parent)
            else:
                import os
                output_dir = os.path.expanduser("~/Desktop")
        idioma_destino = get_config("traduccion.idioma_destino", "es")
        expected_srt = Path(output_dir) / f"{file_stem}.{formato}"
        if expected_srt.exists():
            on_log(f"Found existing subtitles: {expected_srt.name}")
            from ..stages.format import cargar_desde_srt
            try:
                subtitulos = cargar_desde_srt(str(expected_srt))
                if subtitulos:
                    segment_list = [
                        {"start": s.start, "end": s.end, "text": s.text}
                        for s in subtitulos
                    ]
                    on_log(f"[OK] Loaded {len(segment_list)} segments from existing SRT (lang={idioma_destino})")
                    on_progress(item_id, 70.0, "Existing SRT loaded")
                    context["segments"] = segment_list
                    context["original_lang"] = idioma_destino
                    return StageResult(True, data={
                        "segments": segment_list,
                        "original_lang": idioma_destino,
                        "segment_count": len(segment_list),
                    })
            except Exception as e:
                on_log(f"[WARN] Fallback to Whisper: existing SRT load failed ({e})")

        if not self._model and not self.load_model(on_log):
            return StageResult(False, error="Whisper model not available")

        audio_path = context.get("audio_path")
        if not audio_path or not Path(audio_path).exists():
            return StageResult(False, error="No audio file available")

        detect_lang = get_config("whisper.detectar_idioma", True)
        task = get_config("whisper.task", "transcribe")
        beam_size = get_config("whisper.beam_size", 5)
        best_of = get_config("whisper.best_of", 5)
        temperature = get_config("whisper.temperature", 0.0)
        vad = get_config("whisper.vad_filter", True)
        condition = get_config("whisper.condition_on_previous_text", True)
        word_ts = get_config("whisper.word_timestamps", True)

        # Language detection
        original_lang = "en"
        if detect_lang:
            on_log("Detecting language...")
            lang, prob = self._detect_language(audio_path)
            if lang and lang != "auto":
                original_lang = lang
                on_log(f"Language detected: {lang} (prob={prob:.2f})")
            else:
                on_log(f"[WARN] Language detection failed ({lang}), using auto-detect")

        # Pass lang to whisper
        whisper_opts = {
            "task": task,
            "beam_size": beam_size,
            "best_of": best_of,
            "temperature": temperature,
            "vad_filter": vad,
            "condition_on_previous_text": condition if task != "translate" else False,
            "word_timestamps": word_ts,
        }
        if detect_lang and original_lang not in ("en", "auto"):
            whisper_opts["language"] = original_lang
        _DIFFICULT_LANG = {"ja", "zh", "ko", "ar", "he", "hi", "th", "vi"}
        _translate_override = False
        if detect_lang and original_lang not in ("en", "auto"):
            if original_lang in _DIFFICULT_LANG:
                whisper_opts["task"] = "translate"
                original_lang = "en"
                _translate_override = True
            else:
                whisper_opts["task"] = "transcribe"

        if should_cancel():
            return StageResult(False, error="Cancelled before transcription")

        on_log("Transcribing...")
        on_progress(item_id, 20.0, "Transcribing...")

        try:
            segments, info = self._model.transcribe(audio_path, **whisper_opts)

            if info and info.language:
                if not _translate_override:
                    original_lang = info.language

            segment_list: List[Dict[str, Any]] = []
            seg_count = 0
            for seg in segments:
                if should_cancel():
                    return StageResult(False, error="Cancelled during transcription")
                segment_list.append({
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                })
                seg_count += 1
                if seg_count % 10 == 0:
                    pct = min(20.0 + seg_count * 0.5, 65.0)
                    on_progress(item_id, pct, "Transcribing...")

            logger.info("Transcribed %d segments", len(segment_list))
            on_log(f"[OK] Transcribed {len(segment_list)} segments")

            context["segments"] = segment_list
            context["original_lang"] = original_lang
            return StageResult(True, data={
                "segments": segment_list,
                "original_lang": original_lang,
                "segment_count": len(segment_list),
            })

        except Exception as e:
            logger.exception("Transcription error: %s", e)
            return StageResult(False, error=f"Transcription failed: {e}")

    def _detect_language(self, audio_path: str) -> Tuple[Optional[str], float]:
        """Detect audio language using Whisper on first 30s."""
        try:
            sample = self._extract_sample(audio_path)
            if sample is None or len(sample) < 16000:
                return None, 0.0
            segments, info = self._model.transcribe(
                sample, language=None, task="transcribe",
                beam_size=1, best_of=1, vad_filter=False, temperature=0,
            )
            for _ in segments:
                pass
            if info and info.language:
                return info.language, info.language_probability
            return None, 0.0
        except Exception as e:
            logger.warning("Language detection failed: %s", e)
            return None, 0.0

    @staticmethod
    def _extract_sample(audio_path: str, duration_s: float = 30, sr: int = 16000) -> Optional[Any]:
        """Extract audio sample for language detection."""
        import numpy as np
        import subprocess
        ffmpeg = None
        import shutil, sys
        from pathlib import Path
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            p = Path(sys._MEIPASS) / "ffmpeg"
            if p.exists():
                ffmpeg = str(p)
        if not ffmpeg:
            ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return None

        cmd = [
            ffmpeg, "-i", audio_path, "-t", str(duration_s),
            "-f", "s16le", "-acodec", "pcm_s16le",
            "-ar", str(sr), "-ac", "1", "-y", "pipe:1",
        ]
        flags = 0x08000000 if __import__("os").name == "nt" else 0
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=duration_s + 10, creationflags=flags)
            if r.returncode != 0:
                return None
            raw = r.stdout
            return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        except Exception as e:
            logger.warning("Sample extraction error: %s", e)
            return None
