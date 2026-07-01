"""Subtitle formatting stage with professional formatting pipeline."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .base import PipelineStage, StageResult
from ...core import get_logger
from ...config import get_config

logger = get_logger("stage.format")

# Streaming standards
MAX_CARACTERES_POR_LINEA = 42
MAX_LINEAS_POR_SUBTITULO = 2
DURACION_MINIMA_MS = 1500
DURACION_MAXIMA_MS = 7000
CARACTERES_MINIMOS_JUSTIFICACION = 30


@dataclass
class Subtitulo:
    index: int
    start: float
    end: float
    text: str

    def duration_ms(self) -> int:
        return max(int((self.end - self.start) * 1000), 0)

    def word_count(self) -> int:
        return len(self.text.split())

    def lines(self) -> List[str]:
        return self.text.split('\n')

    def to_srt(self) -> str:
        return f"{self.index}\n{_ts_srt(self.start)} --> {_ts_srt(self.end)}\n{self.text}\n"


class FormatStage(PipelineStage):
    """Format subtitles as SRT/ASS/VTT/TXT with professional formatting."""

    name = "format"

    def execute(
        self,
        item_id: str,
        context: Dict[str, Any],
        on_progress: Callable,
        on_log: Callable,
        should_cancel: Callable[[], bool],
    ) -> StageResult:
        segments = context.get("segments")
        if not segments:
            return StageResult(False, error="No segments to format")

        formato = get_config("salida.formato", "srt")
        file_stem = context.get("file_stem", "output")
        output_dir = self._get_output_dir(context)

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        subtitulos = [
            Subtitulo(
                index=i + 1,
                start=seg.get("start", 0),
                end=seg.get("end", 0),
                text=seg.get("text", "").strip(),
            )
            for i, seg in enumerate(segments)
        ]

        try:
            on_log(f"Formatting {len(subtitulos)} subtitles...")

            subtitulos = _apply_formatting(subtitulos)

            on_log(f"Writing {len(subtitulos)} subtitles as {formato.upper()}...")
            salida_path = output_dir / f"{file_stem}.{formato}"
            contenido = _formatear(subtitulos, formato)
            salida_path.write_text(contenido, encoding="utf-8-sig")

            on_progress(item_id, 98.0, "Writing subtitles...")
            on_log(f"[OK] Saved: {salida_path}")

            context["subtitle_path"] = str(salida_path)
            context["output_path"] = str(salida_path)
            context["output_format"] = formato
            context["output_dir"] = str(output_dir)

            stats = _get_statistics(subtitulos)
            on_log(f"[STATS] {stats['total_subtitulos']} subs, "
                   f"{stats['total_palabras']} words, "
                   f"avg {stats['promedio_duracion_ms']}ms")

            if get_config("procesamiento.generar_txt", False):
                txt_path = output_dir / f"{file_stem}.txt"
                txt_path.write_text(_to_txt(subtitulos), encoding="utf-8-sig")
                on_log(f"[OK] TXT saved: {txt_path}")

            return StageResult(True, data={
                "output_path": str(salida_path),
                "output_format": formato,
                "subtitle_count": len(subtitulos),
                "statistics": stats,
            })

        except Exception as e:
            logger.exception("Format error: %s", e)
            return StageResult(False, error=f"Failed to write subtitles: {e}")

    @staticmethod
    def _get_output_dir(context: Dict[str, Any]) -> str:
        user_dir = get_config("salida.directorio", "")
        if user_dir and Path(user_dir).exists():
            return user_dir
        ruta = context.get("ruta", "")
        if ruta and Path(ruta).parent.exists():
            return str(Path(ruta).parent)
        import os
        return os.path.expanduser("~/Desktop")


# --- Formatting pipeline ---

def _apply_formatting(subtitulos: List[Subtitulo]) -> List[Subtitulo]:
    """Apply professional formatting transforms: line splitting, merging, balancing, duration fixes."""
    cfg_max_chars = get_config("subtitulos.max_chars_por_linea", MAX_CARACTERES_POR_LINEA)
    cfg_max_lineas = get_config("subtitulos.max_lineas_por_subtitulo", MAX_LINEAS_POR_SUBTITULO)
    cfg_min_ms = get_config("subtitulos.duracion_minima_ms", DURACION_MINIMA_MS)
    cfg_max_ms = get_config("subtitulos.duracion_maxima_ms", DURACION_MAXIMA_MS)

    subtitulos = _dividir_lineas_largas(subtitulos, cfg_max_chars, cfg_max_lineas)
    subtitulos = _agrupar_subtitulos_cortos(subtitulos)
    subtitulos = _balancear_lineas(subtitulos, cfg_max_chars)
    subtitulos = _ajustar_duraciones(subtitulos, cfg_min_ms, cfg_max_ms)

    for i, sub in enumerate(subtitulos):
        sub.index = i + 1

    return subtitulos


def _dividir_lineas_largas(
    subtitulos: List[Subtitulo],
    max_chars: int,
    max_lineas: int,
) -> List[Subtitulo]:
    """Split subtitles with lines exceeding max_chars at natural pauses."""
    for sub in subtitulos:
        lineas = sub.text.split('\n')
        nuevas = []
        for linea in lineas:
            if len(linea) <= max_chars:
                nuevas.append(linea)
            else:
                nuevas.extend(_dividir_en_pausas_naturales(linea, max_chars))
        if len(nuevas) > max_lineas:
            nuevas = _agrupar_lineas(nuevas, max_lineas, max_chars)
        sub.text = '\n'.join(nuevas)
    return subtitulos


def _dividir_en_pausas_naturales(texto: str, max_chars: int) -> List[str]:
    """Split text at natural pauses (commas, conjunctions, hyphens, spaces)."""
    if len(texto) <= max_chars:
        return [texto]

    separadores = [
        (', ', ', '),
        (' and ', ' and '),
        (' or ', ' or '),
        (' - ', ' - '),
        (' ', ' '),
    ]

    for sep, join_char in separadores:
        if sep not in texto:
            continue
        partes = texto.split(sep)
        lineas = []
        linea_actual = ""
        for i, parte in enumerate(partes):
            prefijo = "" if i == 0 else join_char
            candidato = linea_actual + prefijo + parte
            if len(candidato) <= max_chars:
                linea_actual = candidato
            else:
                if linea_actual:
                    lineas.append(linea_actual)
                linea_actual = parte
        if linea_actual:
            lineas.append(linea_actual)
        if all(len(l) <= max_chars for l in lineas):
            return lineas

    return [texto[i:i+max_chars] for i in range(0, len(texto), max_chars)]


def _agrupar_lineas(
    lineas: List[str],
    max_lineas: int,
    max_chars: int,
) -> List[str]:
    """Group excess lines staying within character budget."""
    if len(lineas) <= max_lineas:
        return lineas
    resultado = []
    i = 0
    while i < len(lineas):
        grupo = [lineas[i]]
        total_len = len(lineas[i])
        i += 1
        while i < len(lineas) and len(grupo) < max_lineas:
            nueva = total_len + 1 + len(lineas[i])
            if nueva <= max_chars * max_lineas:
                grupo.append(lineas[i])
                total_len = nueva
                i += 1
            else:
                break
        resultado.append('\n'.join(grupo))
    return resultado


def _agrupar_subtitulos_cortos(subtitulos: List[Subtitulo]) -> List[Subtitulo]:
    """Merge very short subtitles (<15 chars AND <1500ms) with the next."""
    if len(subtitulos) < 2:
        return subtitulos
    resultado = []
    i = 0
    while i < len(subtitulos):
        cur = subtitulos[i]
        if (i + 1 < len(subtitulos)
                and len(cur.text) < 15
                and cur.duration_ms() < 1500):
            nxt = subtitulos[i + 1]
            resultado.append(Subtitulo(
                index=cur.index,
                start=cur.start,
                end=nxt.end,
                text=f"{cur.text} {nxt.text}",
            ))
            i += 2
        else:
            resultado.append(cur)
            i += 1
    return resultado


def _balancear_lineas(subtitulos: List[Subtitulo], max_chars: int) -> List[Subtitulo]:
    """Balance two-line subtitles by redistributing words evenly."""
    for sub in subtitulos:
        lineas = sub.text.split('\n')
        if len(lineas) != 2:
            continue
        a, b = lineas
        if len(a) > len(b) * 1.5 or len(b) > len(a) * 1.5:
            palabras = sub.text.split()
            mid = len(palabras) // 2
            na = ' '.join(palabras[:mid])
            nb = ' '.join(palabras[mid:])
            if len(na) <= max_chars and len(nb) <= max_chars:
                sub.text = f"{na}\n{nb}"
    return subtitulos


def _ajustar_duraciones(
    subtitulos: List[Subtitulo],
    min_ms: int,
    max_ms: int,
) -> List[Subtitulo]:
    """Clamp durations and resolve overlaps between consecutive subtitles."""
    for i, sub in enumerate(subtitulos):
        dur = sub.duration_ms()
        if dur < min_ms:
            sub.end = sub.start + (min_ms / 1000.0)
        elif dur > max_ms:
            sub.end = sub.start + (max_ms / 1000.0)
        if i + 1 < len(subtitulos):
            nxt = subtitulos[i + 1]
            if sub.end > nxt.start:
                diff = sub.end - nxt.start
                sub.end -= diff / 2
                nxt.start += diff / 2
    return subtitulos


# --- Serializers ---

def _formatear(subtitulos: List[Subtitulo], fmt: str) -> str:
    if fmt == "ass":
        return _to_ass(subtitulos)
    elif fmt == "vtt":
        return _to_vtt(subtitulos)
    elif fmt == "txt":
        return _to_txt(subtitulos)
    else:
        return _to_srt(subtitulos)


def _to_srt(subtitulos: List[Subtitulo]) -> str:
    return "\n".join(s.to_srt() for s in subtitulos)


def _to_vtt(subtitulos: List[Subtitulo]) -> str:
    lines = ["WEBVTT", ""]
    for s in subtitulos:
        lines.append(f"{_ts_vtt(s.start)} --> {_ts_vtt(s.end)}")
        lines.append(s.text)
        lines.append("")
    return "\n".join(lines)


def _to_ass(subtitulos: List[Subtitulo]) -> str:
    header = """[Script Info]
ScriptType: v4.00+
Collisions: Normal
PlayResX: 384
PlayResY: 288
Timer: 100.0000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,16,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,1,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for s in subtitulos:
        events.append(
            f"Dialogue: 0,{_ts_ass(s.start)},{_ts_ass(s.end)},Default,,0,0,0,,{s.text}"
        )
    return header + "\n".join(events)


def _to_txt(subtitulos: List[Subtitulo]) -> str:
    texts = [sub.text.replace('\n', ' ') for sub in subtitulos]
    return ' '.join(texts)


# --- Helpers ---

def _ts_srt(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _ts_vtt(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _ts_ass(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:01d}:{s:05.2f}"


# --- Statistics ---

def _get_statistics(subtitulos: List[Subtitulo]) -> Dict[str, Any]:
    if not subtitulos:
        return {
            "total_subtitulos": 0,
            "total_palabras": 0,
            "total_caracteres": 0,
            "duracion_total_ms": 0,
            "promedio_duracion_ms": 0,
            "promedio_palabras_por_sub": 0,
        }
    total_palabras = sum(s.word_count() for s in subtitulos)
    total_caracteres = sum(len(s.text) for s in subtitulos)
    duracion_total = sum(s.duration_ms() for s in subtitulos)
    n = len(subtitulos)
    return {
        "total_subtitulos": n,
        "total_palabras": total_palabras,
        "total_caracteres": total_caracteres,
        "duracion_total_ms": duracion_total,
        "promedio_duracion_ms": duracion_total // n,
        "promedio_palabras_por_sub": total_palabras // n,
    }


# --- Utility ---

def limpiar_subtitulo(texto: str) -> str:
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = re.sub(r"\{\\.*?\}", "", texto)
    return texto.strip()


def cargar_desde_srt(ruta_srt: str) -> List[Subtitulo]:
    with open(ruta_srt, 'r', encoding='utf-8-sig') as f:
        contenido = f.read()
    bloques = re.split(r'\n\s*\n', contenido.strip())
    subtitulos = []
    for bloque in bloques:
        lineas = bloque.strip().split('\n')
        if len(lineas) < 3:
            continue
        try:
            numero = int(lineas[0].strip())
        except (ValueError, IndexError):
            continue
        match = re.match(
            r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*'
            r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})',
            lineas[1].strip()
        )
        if not match:
            continue
        g = match.groups()
        start_ms = (int(g[0])*3600 + int(g[1])*60 + int(g[2]))*1000 + int(g[3])
        end_ms = (int(g[4])*3600 + int(g[5])*60 + int(g[6]))*1000 + int(g[7])
        texto = limpiar_subtitulo('\n'.join(lineas[2:]))
        subtitulos.append(Subtitulo(
            index=numero,
            start=start_ms / 1000.0,
            end=end_ms / 1000.0,
            text=texto,
        ))
    return subtitulos
