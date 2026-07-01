"""Minimal find/replace dialog — delegates to editor_operations."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox,
)

from ...utils.editor_model import SubtitleDocument
from ...utils.editor_operations import find_text, replace_text
from ..i18n import _


class SearchDialog(QDialog):
    def __init__(self, doc: SubtitleDocument, parent=None):
        super().__init__(parent)
        self._doc = doc
        self._search_pos = 0
        self.setWindowTitle(_("Buscar / Reemplazar"))
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Search row
        row1 = QHBoxLayout()
        row1.addWidget(QLabel(_("Buscar:")))
        self._search_input = QLineEdit()
        row1.addWidget(self._search_input)
        layout.addLayout(row1)

        # Replace row
        row2 = QHBoxLayout()
        row2.addWidget(QLabel(_("Reemplazar:")))
        self._replace_input = QLineEdit()
        row2.addWidget(self._replace_input)
        layout.addLayout(row2)

        # Case sensitive checkbox
        self._case_cb = QCheckBox(_("Mayus/minus exacto"))
        layout.addWidget(self._case_cb)

        # Buttons
        btn_row = QHBoxLayout()
        self._find_btn = QPushButton(_("Buscar siguiente"))
        self._find_btn.clicked.connect(self._on_find)
        btn_row.addWidget(self._find_btn)

        self._replace_btn = QPushButton(_("Reemplazar"))
        self._replace_btn.clicked.connect(self._on_replace)
        btn_row.addWidget(self._replace_btn)

        self._replace_all_btn = QPushButton(_("Reemplazar todo"))
        self._replace_all_btn.clicked.connect(self._on_replace_all)
        btn_row.addWidget(self._replace_all_btn)

        btn_row.addStretch()
        close_btn = QPushButton(_("Cerrar"))
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._search_input.returnPressed.connect(self._on_find)
        self._search_input.setFocus()

    def _case_sensitive(self) -> bool:
        return self._case_cb.isChecked()

    def _on_find(self) -> None:
        query = self._search_input.text()
        if not query:
            return
        results = find_text(self._doc, query, case_sensitive=self._case_sensitive())
        if results:
            self.parent()._select_entry(results[0][0]) if hasattr(self.parent(), "_select_entry") else None

    def _on_replace(self) -> None:
        search = self._search_input.text()
        repl = self._replace_input.text()
        if not search:
            return
        count = replace_text(self._doc, search, repl, case_sensitive=self._case_sensitive())
        if count:
            self._emit_refresh()

    def _on_replace_all(self) -> None:
        search = self._search_input.text()
        repl = self._replace_input.text()
        if not search:
            return
        count = replace_text(self._doc, search, repl, case_sensitive=self._case_sensitive())
        if count:
            self._emit_refresh()

    def _emit_refresh(self) -> None:
        p = self.parent()
        if hasattr(p, "_refresh_table"):
            p._refresh_table()
