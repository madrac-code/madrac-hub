"""Load/save subtitle files (SRT/VTT/ASS) for the editor model."""

import re
from pathlib import Path
from typing import List, Optional

from ..core import write_text
from .editor_model import SubtitleDocument, SubtitleEntry

_SRT_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)


def _parse_timestamp(ts: str) -> int:
    m = re.match(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", ts)
    if not m:
        return 0
    g = m.groups()
    return (int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2])) * 1000 + int(g[3])


def _ts_srt(ms: int) -> str:
    total = ms // 1000
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    remain = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{remain:03d}"


def _ts_vtt(ms: int) -> str:
    total = ms // 1000
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    remain = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d}.{remain:03d}"


def _ts_ass(ms: int) -> str:
    total = ms / 1000.0
    h = int(total // 3600)
    m = int((total % 3600) // 60)
    s = total % 60
    return f"{h}:{m:01d}:{s:05.2f}"


def _clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\{\\.*?\}", "", text)
    return text.strip()


def load_srt(path: str) -> SubtitleDocument:
    with open(path, "r", encoding="utf-8-sig") as f:
        content = f.read()
    blocks = re.split(r"\n\s*\n", content.strip())
    entries: List[SubtitleEntry] = []
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        try:
            idx = int(lines[0].strip())
        except (ValueError, IndexError):
            continue
        m = _SRT_RE.match(lines[1].strip())
        if not m:
            continue
        g = m.groups()
        start = (int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2])) * 1000 + int(g[3])
        end = (int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6])) * 1000 + int(g[7])
        text = _clean_text("\n".join(lines[2:]))
        entries.append(SubtitleEntry(idx, start, end, text))
    return SubtitleDocument(entries=entries, path=Path(path), modified=False)


def save_srt(doc: SubtitleDocument, path: Optional[str] = None) -> str:
    out = path if path else (str(doc.path) if doc.path else "output.srt")
    lines: List[str] = []
    for e in doc.entries:
        lines.append(str(e.index))
        lines.append(f"{_ts_srt(e.start_ms)} --> {_ts_srt(e.end_ms)}")
        lines.append(e.text)
        lines.append("")
    body = "\n".join(lines)
    write_text(out, body)
    doc.path = Path(out)
    doc.modified = False
    return out


def load_vtt(path: str) -> SubtitleDocument:
    with open(path, "r", encoding="utf-8-sig") as f:
        content = f.read()
    lines = content.split("\n")
    if lines and lines[0].strip() == "WEBVTT":
        lines = lines[1:]
    blocks = re.split(r"\n\s*\n", "\n".join(lines).strip())
    entries: List[SubtitleEntry] = []
    idx = 1
    for block in blocks:
        block_lines = block.strip().split("\n")
        if len(block_lines) < 2:
            continue
        ts_line = block_lines[0].strip()
        m = re.match(
            r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*"
            r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})",
            ts_line,
        )
        if not m:
            continue
        g = m.groups()
        start = (int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2])) * 1000 + int(g[3])
        end = (int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6])) * 1000 + int(g[7])
        text = _clean_text("\n".join(block_lines[1:]))
        entries.append(SubtitleEntry(idx, start, end, text))
        idx += 1
    return SubtitleDocument(entries=entries, path=Path(path), modified=False)


def save_vtt(doc: SubtitleDocument, path: Optional[str] = None) -> str:
    out = path or (str(doc.path.with_suffix(".vtt")) if doc.path else "output.vtt")
    lines = ["WEBVTT", ""]
    for e in doc.entries:
        lines.append(f"{_ts_vtt(e.start_ms)} --> {_ts_vtt(e.end_ms)}")
        lines.append(e.text)
        lines.append("")
    write_text(out, "\n".join(lines))
    doc.path = Path(out)
    doc.modified = False
    return out


def load_ass(path: str) -> SubtitleDocument:
    with open(path, "r", encoding="utf-8-sig") as f:
        content = f.read()
    entries: List[SubtitleEntry] = []
    idx = 1
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 10:
            continue
        start_parts = parts[1].strip().split(":")
        end_parts = parts[2].strip().split(":")
        if len(start_parts) != 3 or len(end_parts) != 3:
            continue
        try:
            start = (
                int(start_parts[0]) * 3600000
                + int(start_parts[1]) * 60000
                + int(float(start_parts[2]) * 1000)
            )
            end = (
                int(end_parts[0]) * 3600000
                + int(end_parts[1]) * 60000
                + int(float(end_parts[2]) * 1000)
            )
        except ValueError:
            continue
        text = _clean_text(parts[9])
        entries.append(SubtitleEntry(idx, start, end, text))
        idx += 1
    return SubtitleDocument(entries=entries, path=Path(path), modified=False)


def save_ass(doc: SubtitleDocument, path: Optional[str] = None) -> str:
    out = path or (str(doc.path.with_suffix(".ass")) if doc.path else "output.ass")
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
    events: List[str] = []
    for e in doc.entries:
        events.append(
            f"Dialogue: 0,{_ts_ass(e.start_ms)},{_ts_ass(e.end_ms)},Default,,0,0,0,,{e.text}"
        )
    write_text(out, header + "\n".join(events))
    doc.path = Path(out)
    doc.modified = False
    return out


def detect_format(path: str) -> str:
    ext = Path(path).suffix.lower()
    fmt_map = {".srt": "srt", ".vtt": "vtt", ".ass": "ass", ".ssa": "ass"}
    return fmt_map.get(ext, "srt")
