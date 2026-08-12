"""Translation MCP tools — uses translator.GestorTraduccion (same engine as pipeline)."""
from __future__ import annotations
from typing import Any
from pathlib import Path


def translate_subtitles(app_state: dict[str, Any]):
    async def _translate_subtitles(
        archivo_srt: str,
        idioma_destino: str,
        motor: str = "marianmt",
    ) -> str:
        """
        Translate a .srt file to the target language.

        Uses the same GestorTraduccion engine as the pipeline's TranslateStage.

        Args:
            archivo_srt: Absolute path to the source .srt file
            idioma_destino: Target language code (e.g. 'en', 'fr', 'pt')
            motor: Translation engine ('marianmt', 'argos', 'google'). Default: 'marianmt'

        Returns:
            Path to the translated .srt file, or error message.
        """
        srt_path = Path(archivo_srt)
        if not srt_path.exists():
            return f"Error: file not found: {archivo_srt}"
        if srt_path.suffix.lower() not in (".srt", ".ass", ".ssa"):
            return f"Error: not a subtitle file: {archivo_srt}"

        try:
            import importlib
            import sys as _sys

            root = Path(__file__).resolve().parents[4]
            if str(root) not in _sys.path:
                _sys.path.insert(0, str(root))
            src = root / "src"
            if src.is_dir() and str(src) not in _sys.path:
                _sys.path.insert(0, str(src))

            from ...pipeline.stages.format import cargar_desde_srt, _ts_srt

            subtitulos = cargar_desde_srt(str(srt_path))
            if not subtitulos:
                return f"Error: no subtitles parsed from {archivo_srt}"

            trans_mod = importlib.import_module("translator")
            gestor = trans_mod.GestorTraduccion.desde_config()
            gestor.idioma_destino = idioma_destino
            gestor.motor_tipo = motor
            if gestor.motor_tipo != motor:
                from importlib import import_module as _im
                cls = _im("translator").GestorTraduccion
                gestor = cls(motor=motor, idioma_destino=idioma_destino)

            textos = [s.text for s in subtitulos]
            traducciones = gestor.traducir_lote(
                textos,
                idioma_origen="auto",
                debe_cancelar=lambda: False,
            )
            if len(traducciones) != len(textos):
                return "Error: translation returned mismatched count"

            output_path = srt_path.with_name(f"{srt_path.stem}_{idioma_destino}{srt_path.suffix}")
            contenido = "\n".join(
                f"{i + 1}\n{_ts_srt(s.start)} --> {_ts_srt(s.end)}\n{traducciones[i]}"
                for i, s in enumerate(subtitulos)
            )
            output_path.write_text(contenido + "\n", encoding="utf-8-sig")
            return str(output_path)
        except Exception as e:
            return f"Error translating: {e}"
    return _translate_subtitles
