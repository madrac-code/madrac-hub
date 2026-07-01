"""Pure editing operations on SubtitleDocument (no Qt)."""

import re
from typing import List, Optional, Tuple

from .editor_model import SubtitleDocument, SubtitleEntry


def shift_times(doc: SubtitleDocument, delta_ms: int) -> None:
    doc.shift(delta_ms)


def change_fps(
    doc: SubtitleDocument,
    source_fps: float,
    target_fps: float,
) -> None:
    ratio = target_fps / source_fps
    for e in doc.entries:
        e.start_ms = _round_ms(e.start_ms * ratio)
        e.end_ms = _round_ms(e.end_ms * ratio)
    doc.modified = True


def merge_entries(
    doc: SubtitleDocument,
    first_index: int,
    second_index: int,
) -> bool:
    a = doc.get(first_index)
    b = doc.get(second_index)
    if a is None or b is None:
        return False
    a.end_ms = b.end_ms
    a.text = f"{a.text}\n{b.text}"
    doc.entries.remove(b)
    doc.renumber()
    doc.modified = True
    return True


def split_entry(
    doc: SubtitleDocument,
    index: int,
    split_ms: int,
) -> bool:
    e = doc.get(index)
    if e is None:
        return False
    if split_ms <= e.start_ms or split_ms >= e.end_ms:
        return False
    mid_ms = (e.start_ms + e.end_ms) // 2
    gap = (e.end_ms - e.start_ms) // 4
    lines = e.text.split("\n")
    if len(lines) < 2:
        idx = max(1, len(e.text) // 2)
        first_text = e.text[:idx].strip()
        second_text = e.text[idx:].strip()
    else:
        half = len(lines) // 2
        first_text = "\n".join(lines[:half])
        second_text = "\n".join(lines[half:])
    e.end_ms = split_ms - gap
    new_entry = SubtitleEntry(
        index=0,
        start_ms=split_ms + gap,
        end_ms=max(e.end_ms, split_ms + gap + 1000),
        text=second_text,
    )
    e.text = first_text
    pos = doc.entries.index(e) + 1
    doc.entries.insert(pos, new_entry)
    doc.renumber()
    doc.modified = True
    return True


def remove_entry(doc: SubtitleDocument, index: int) -> bool:
    e = doc.get(index)
    if e is None:
        return False
    doc.entries.remove(e)
    doc.renumber()
    doc.modified = True
    return True


def insert_entry(doc: SubtitleDocument, entry: SubtitleEntry) -> None:
    doc.entries.append(entry)
    doc.sort()
    doc.renumber()
    doc.modified = True


def renumber(doc: SubtitleDocument) -> None:
    doc.renumber()


def find_text(
    doc: SubtitleDocument,
    query: str,
    case_sensitive: bool = False,
) -> List[Tuple[int, int, str]]:
    if not case_sensitive:
        query = query.lower()
    results: List[Tuple[int, int, str]] = []
    for e in doc.entries:
        text = e.text if case_sensitive else e.text.lower()
        if query in text:
            results.append((e.index, e.start_ms, e.text))
    return results


def replace_text(
    doc: SubtitleDocument,
    search: str,
    replacement: str,
    case_sensitive: bool = False,
) -> int:
    count = 0
    for e in doc.entries:
        if case_sensitive:
            new_text = e.text.replace(search, replacement)
        else:
            pattern = re.compile(re.escape(search), re.IGNORECASE)
            new_text = pattern.sub(replacement, e.text)
        if new_text != e.text:
            e.text = new_text
            count += 1
    if count:
        doc.modified = True
    return count


def trim_trailing_spaces(doc: SubtitleDocument) -> int:
    count = 0
    for e in doc.entries:
        trimmed = "\n".join(line.rstrip() for line in e.text.split("\n"))
        if trimmed != e.text:
            e.text = trimmed
            count += 1
    if count:
        doc.modified = True
    return count


def adjust_duration(
    doc: SubtitleDocument,
    min_ms: int = 1500,
    max_ms: int = 7000,
) -> int:
    count = 0
    for e in doc.entries:
        dur = e.duration_ms()
        if dur < min_ms:
            e.end_ms = e.start_ms + min_ms
            count += 1
        elif dur > max_ms:
            e.end_ms = e.start_ms + max_ms
            count += 1
    if count:
        doc.modified = True
    return count


def _round_ms(val: float) -> int:
    return int(round(val))
