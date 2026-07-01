"""Pure domain model for the subtitle editor (no Qt)."""

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional


@dataclass(slots=True)
class SubtitleEntry:
    index: int
    start_ms: int
    end_ms: int
    text: str

    def duration_ms(self) -> int:
        return max(self.end_ms - self.start_ms, 0)

    def as_tuple(self) -> tuple:
        return (self.index, self.start_ms, self.end_ms, self.text)

    def clone(self) -> "SubtitleEntry":
        return SubtitleEntry(self.index, self.start_ms, self.end_ms, self.text)


@dataclass
class SubtitleDocument:
    entries: List[SubtitleEntry] = field(default_factory=list)
    path: Optional[Path] = None
    modified: bool = False

    # ── queries ──────────────────────────────────────────────────────────

    def duration_ms(self) -> int:
        if not self.entries:
            return 0
        return max(e.end_ms for e in self.entries) - min(e.start_ms for e in self.entries)

    def count(self) -> int:
        return len(self.entries)

    def get(self, index: int) -> Optional[SubtitleEntry]:
        for e in self.entries:
            if e.index == index:
                return e
        return None

    # ── mutations ────────────────────────────────────────────────────────

    def clone(self) -> "SubtitleDocument":
        return SubtitleDocument(
            entries=[e.clone() for e in self.entries],
            path=self.path,
            modified=self.modified,
        )

    def sort(self) -> None:
        self.entries.sort(key=lambda e: (e.start_ms, e.index))
        self.modified = True

    def renumber(self) -> None:
        for i, e in enumerate(self.entries, 1):
            e.index = i
        self.modified = True

    def shift(self, delta_ms: int) -> None:
        for e in self.entries:
            e.start_ms = max(e.start_ms + delta_ms, 0)
            e.end_ms = max(e.end_ms + delta_ms, 0)
        self.modified = True

    # ── validation ──────────────────────────────────────────────────────

    def validate(self) -> List[str]:
        warnings: List[str] = []
        for i, e in enumerate(self.entries):
            if e.start_ms < 0:
                warnings.append(f"Entry #{e.index}: start_ms < 0 ({e.start_ms})")
            if e.end_ms <= e.start_ms:
                warnings.append(f"Entry #{e.index}: end_ms ({e.end_ms}) <= start_ms ({e.start_ms})")
            if e.index <= 0:
                warnings.append(f"Entry #{e.index}: index <= 0")
            if not e.text.strip():
                warnings.append(f"Entry #{e.index}: empty text")
        for i in range(len(self.entries) - 1):
            curr = self.entries[i]
            nxt = self.entries[i + 1]
            if curr.end_ms > nxt.start_ms:
                warnings.append(
                    f"Overlap: #{curr.index} ends at {curr.end_ms}ms "
                    f"but #{nxt.index} starts at {nxt.start_ms}ms"
                )
        return warnings

    def has_overlaps(self) -> bool:
        return any(
            self.entries[i].end_ms > self.entries[i + 1].start_ms
            for i in range(len(self.entries) - 1)
        )


# ── HistoryStack (snapshot-based undo/redo) ──────────────────────────────

@dataclass
class HistoryStack:
    _past: List[SubtitleDocument] = field(default_factory=list)
    _future: List[SubtitleDocument] = field(default_factory=list)
    _max: int = 50

    def push(self, doc: SubtitleDocument) -> None:
        self._past.append(doc.clone())
        self._future.clear()
        if len(self._past) > self._max:
            self._past.pop(0)

    def undo(self, doc: SubtitleDocument) -> Optional[SubtitleDocument]:
        if not self._past:
            return None
        self._future.append(doc.clone())
        return self._past.pop()

    def redo(self, doc: SubtitleDocument) -> Optional[SubtitleDocument]:
        if not self._future:
            return None
        self._past.append(doc.clone())
        return self._future.pop()

    def can_undo(self) -> bool:
        return len(self._past) > 0

    def can_redo(self) -> bool:
        return len(self._future) > 0

    def clear(self) -> None:
        self._past.clear()
        self._future.clear()