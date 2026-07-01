"""Editable subtitle navigation list widget."""

import re
from typing import List, Optional

from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton,
    QAbstractItemView, QApplication, QLineEdit,
)

from ...utils.editor_model import SubtitleEntry
from ..i18n import _


def _ms_to_str(ms: int) -> str:
    total = ms // 1000
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    r = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{r:03d}"


_ENTRY_PREFIX = re.compile(
    r"^\[\d+\]\s+\d{2}:\d{2}:\d{2},\d{3}\s*→\s*\d{2}:\d{2}:\d{2},\d{3}\s+"
)


class SubtitleNavigationWidget(QWidget):
    seekRequested = Signal(int)
    subtitleTextChanged = Signal(int, str)
    fragmentAdded = Signal(int)
    editStarted = Signal(int)
    collapsedChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: List[SubtitleEntry] = []
        self._suppress = False
        self._collapsed = False
        self._setup_ui()
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        header = QLabel(_("Subtitulos"))
        header.setStyleSheet("font-weight: bold; font-size: 10pt;")
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.setSpacing(2)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.itemChanged.connect(self._on_item_changed)
        self._list.setMinimumHeight(80)
        self._list.setSelectionMode(QListWidget.SingleSelection)
        self._list.installEventFilter(self)
        layout.addWidget(self._list, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        self._add_btn = QPushButton(_("Agregar fragmento"))
        self._add_btn.setFixedHeight(28)
        self._add_btn.clicked.connect(self._on_add_fragment)
        btn_layout.addStretch()
        btn_layout.addWidget(self._add_btn)
        layout.addLayout(btn_layout)

    # ── Public API ────────────────────────────────────────────────────

    def load_entries(self, entries: List[SubtitleEntry]):
        self._entries = entries
        self._rebuild()

    def highlight_current(self, index: int):
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.data(Qt.UserRole) == index:
                self._list.setCurrentItem(item)
                self._list.scrollToItem(item)
                break

    def insert_fragment(self, entry: SubtitleEntry) -> int:
        self._entries.append(entry)
        self._entries.sort(key=lambda e: (e.start_ms, e.index))
        for i, e in enumerate(self._entries):
            e.index = i + 1
        self._rebuild()
        return entry.index

    def get_entries(self) -> List[SubtitleEntry]:
        return self._entries

    def set_collapsed(self, collapsed: bool) -> None:
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed
        if collapsed:
            self._list.hide()
            self._add_btn.hide()
        else:
            self._list.show()
            self._add_btn.show()
        self.collapsedChanged.emit(collapsed)

    def is_collapsed(self) -> bool:
        return self._collapsed

    def is_editing(self) -> bool:
        """Check if an inline editor is active."""
        return self._list.state() == QAbstractItemView.EditingState

    def destroy(self, *args) -> None:
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self)
        super().destroy(*args)

    def commit_edit(self) -> None:
        """Force-commit the current inline edit (no revert)."""
        editor = self._list.findChild(QLineEdit)
        item = self._list.currentItem()
        if editor and item:
            item.setText(editor.text())
            editor.deleteLater()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            if self.is_editing():
                self.commit_edit()
                return True
        if event.type() == QEvent.FocusOut:
            if isinstance(obj, QLineEdit) and self.is_editing():
                self.commit_edit()
        return super().eventFilter(obj, event)

    # ── Internal ──────────────────────────────────────────────────────

    def _rebuild(self):
        self._suppress = True
        self._list.clear()
        for e in self._entries:
            text = self._format_item(e)
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, e.index)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self._list.addItem(item)
        self._suppress = False

    def _format_item(self, e: SubtitleEntry) -> str:
        start = _ms_to_str(e.start_ms)
        end = _ms_to_str(e.end_ms)
        display_text = e.text.replace("\n", " | ")
        if len(display_text) > 60:
            display_text = display_text[:57] + "..."
        return f"[{e.index}]  {start} → {end}  {display_text}"

    def _on_item_double_clicked(self, item: QListWidgetItem):
        idx = item.data(Qt.UserRole)
        entry = self._find_entry(idx)
        if entry:
            self.seekRequested.emit(entry.start_ms)

    def _on_item_changed(self, item: QListWidgetItem):
        if self._suppress:
            return
        idx = item.data(Qt.UserRole)
        full_text = item.text()
        match = _ENTRY_PREFIX.match(full_text)
        if match:
            new_text = full_text[match.end():].strip()
        else:
            new_text = full_text
        entry = self._find_entry(idx)
        if entry and new_text != entry.text:
            self.editStarted.emit(idx)
            entry.text = new_text
            self.subtitleTextChanged.emit(idx, new_text)
            self._suppress = True
            item.setText(self._format_item(entry))
            self._suppress = False

    def _on_add_fragment(self):
        self.fragmentAdded.emit(0)

    def _find_entry(self, index: int) -> Optional[SubtitleEntry]:
        for e in self._entries:
            if e.index == index:
                return e
        return None
