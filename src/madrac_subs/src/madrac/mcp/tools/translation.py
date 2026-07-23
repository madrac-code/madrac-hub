"""Translation MCP tools."""
from __future__ import annotations
from typing import Any


def translate_subtitles(app_state: dict[str, Any]):
    async def _translate_subtitles(
        archivo_srt: str,
        idioma_destino: str,
    ) -> str:
        """
        Translate a .srt file to the target language.

        Args:
            archivo_srt: Absolute path to the source .srt file
            idioma_destino: Target language code (e.g. 'en', 'fr', 'pt')

        Returns:
            Path to the translated .srt file, or error message.
        """
        config = app_state.get("config")
        if config is None:
            return "Error: config not available"
        try:
            from madrac.translator import Translator
            translator = Translator(config)
            output_path = translator.translate_srt_file(
                archivo_srt, idioma_destino
            )
            return str(output_path)
        except Exception as e:
            return f"Error translating: {e}"
    return _translate_subtitles
