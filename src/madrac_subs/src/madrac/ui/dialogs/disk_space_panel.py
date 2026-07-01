"""V2-style disk space panel widget."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from ...utils.system import disk_usage_by_category, clean_temp, clean_logs, clean_hf_cache
from ..i18n import _

_CATEGORIES = [
    ("whisper", _("Whisper models")),
    ("marian", _("Marian models")),
    ("cache_hf", _("HuggingFace cache")),
    ("logs", _("Logs")),
    ("temp", _("Temporary files")),
]


def _format_size(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}" if unit != "B" else f"{b} B"
        b /= 1024
    return f"{b:.1f} TB"


class DiskSpacePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._labels: dict[str, QLabel] = {}
        self._total_label = QLabel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        for key, title in _CATEGORIES:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{title}:"))
            row.addStretch()
            lbl = QLabel("--")
            lbl.setStyleSheet("font-weight: bold;")
            self._labels[key] = lbl
            row.addWidget(lbl)
            layout.addLayout(row)

        sep = QLabel("─" * 40)
        sep.setStyleSheet("color: #888;")
        layout.addWidget(sep)

        total_row = QHBoxLayout()
        total_row.addWidget(QLabel(_("TOTAL:")))
        total_row.addStretch()
        self._total_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        total_row.addWidget(self._total_label)
        layout.addLayout(total_row)

        layout.addSpacing(8)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton(_("Actualizar"))
        refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(refresh_btn)

        clean_btn = QPushButton(_("Limpiar..."))
        clean_btn.clicked.connect(self._on_clean)
        btn_row.addWidget(clean_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def refresh(self):
        sizes = disk_usage_by_category()
        total = 0
        for key, _ in _CATEGORIES:
            sz = sizes.get(key, 0)
            self._labels[key].setText(_format_size(sz))
            total += sz
        self._total_label.setText(_format_size(total))

    def _on_clean(self):
        from .disk_cleanup_dialog import DiskCleanupDialog
        dlg = DiskCleanupDialog(self)
        if dlg.exec():
            self.refresh()
