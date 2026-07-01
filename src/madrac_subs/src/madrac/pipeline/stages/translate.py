"""Translation stage wrapping GestorTraduccion."""

from typing import Any, Callable, Dict, List, Optional

from .base import PipelineStage, StageResult
from ...core import get_logger
from ...config import get_config

logger = get_logger("stage.translate")


class TranslateStage(PipelineStage):
    """Translate subtitles using the configured engine."""

    name = "translate"

    def __init__(self) -> None:
        super().__init__()
        self._gestor: Any = None

    def _ensure_gestor(self, on_log: Callable) -> bool:
        target_lang = get_config("traduccion.idioma_destino", "es")
        target_motor = get_config("traduccion.motor", "marianmt")
        if self._gestor is not None and self._gestor.idioma_destino == target_lang and self._gestor.motor_tipo == target_motor:
            return True
        try:
            import sys as _sys
            from pathlib import Path as _Path
            _root = _Path(__file__).parent.parent.parent.parent.parent
            _mod_path = str(_root)
            if _mod_path not in _sys.path:
                _sys.path.insert(0, _mod_path)
            _src_path = str(_root / "src")
            if _src_path not in _sys.path:
                _sys.path.insert(0, _src_path)

            import importlib
            _trans_mod = importlib.import_module("translator")
            self._gestor = _trans_mod.GestorTraduccion.desde_config()
            on_log(f"[OK] Translator loaded: {self._gestor.motor_tipo}")
            return True
        except Exception as e:
            logger.exception("Failed to load translation engine: %s", e)
            on_log(f"[ERR] Translator load failed: {e}")
            return False

    def execute(
        self,
        item_id: str,
        context: Dict[str, Any],
        on_progress: Callable,
        on_log: Callable,
        should_cancel: Callable[[], bool],
    ) -> StageResult:
        if not get_config("traduccion.habilitada", True):
            on_log("Translation disabled")
            return StageResult(True, data={"translated": False})

        segments = context.get("segments")
        if not segments:
            # Maybe embedded subs were used
            return StageResult(True, data={"translated": False})

        original_lang = context.get("original_lang", "en")
        idioma_destino = get_config("traduccion.idioma_destino", "es")
        if original_lang == idioma_destino:
            on_log(f"Original language is {original_lang} - no translation needed")
            return StageResult(True, data={"translated": False})

        if not self._ensure_gestor(on_log):
            return StageResult(False, error="Translation engine not available")

        # Build subtitle texts
        textos = [seg.get("text", "") for seg in segments]

        def on_lote(lote: int, total: int) -> None:
            pct = 75.0 + (20.0 * lote / total) if total > 0 else 85.0
            on_progress(item_id, pct, f"Translating... ({lote}/{total})")

        try:
            on_log(f"Translating {len(textos)} segments ({original_lang} -> {idioma_destino})...")
            traducciones = self._gestor.traducir_lote(
                textos,
                idioma_origen=original_lang,
                debe_cancelar=should_cancel,
                on_progreso=on_lote,
            )

            # Rebuild segments with translated text
            translated = []
            for i, seg in enumerate(segments):
                txt = traducciones[i] if i < len(traducciones) else seg.get("text", "")
                translated.append({
                    "start": seg.get("start", 0),
                    "end": seg.get("end", 0),
                    "text": txt,
                })

            context["segments"] = translated
            if translated:
                on_log(f"[OK] Translation complete. Sample: '{translated[0]['text'][:80]}'")
            else:
                on_log("[OK] Translation complete")
            return StageResult(True, data={"translated": True, "count": len(translated)})

        except Exception as e:
            logger.exception("Translation error: %s", e)
            return StageResult(False, error=f"Translation failed: {e}")
