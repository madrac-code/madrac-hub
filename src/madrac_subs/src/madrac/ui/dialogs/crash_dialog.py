"""Crash dialog shown on unhandled exceptions."""

import platform
import sys
import textwrap
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QApplication,
)

from ... import __version__
from ...core.paths import get_log_path
from ..i18n import _


class CrashDialog(QDialog):
    def __init__(self, summary: str, details: str, parent=None):
        super().__init__(parent)
        self._details = details
        self.setWindowTitle(_("Error no recuperable"))
        self.setMinimumSize(520, 360)
        self.setModal(True)

        layout = QVBoxLayout(self)

        icon = QLabel(f"\u26A0\uFE0F  {_('MADRAC-SUBS')}")
        icon.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(icon)

        msg = QLabel(
            _("La aplicacion ha encontrado un error inesperado.\nPuedes copiar los detalles, abrir el log, o reportar el problema.")
        )
        msg.setWordWrap(True)
        layout.addWidget(msg)

        self._summary = QLabel(summary)
        self._summary.setWordWrap(True)
        self._summary.setStyleSheet("color: #c00; font-weight: bold; padding: 8px 0;")
        layout.addWidget(self._summary)

        self._detail_view = QPlainTextEdit()
        self._detail_view.setReadOnly(True)
        self._detail_view.setPlainText(self._build_report())
        self._detail_view.setMaximumBlockCount(200)
        layout.addWidget(self._detail_view)

        row = QHBoxLayout()
        copy_btn = QPushButton(_("Copiar detalles"))
        copy_btn.clicked.connect(self._on_copy)
        row.addWidget(copy_btn)

        log_btn = QPushButton(_("Abrir log"))
        log_btn.clicked.connect(self._on_open_log)
        row.addWidget(log_btn)

        report_btn = QPushButton(_("Reportar problema"))
        report_btn.clicked.connect(self._on_report)
        row.addWidget(report_btn)

        row.addStretch()

        close_btn = QPushButton(_("Cerrar"))
        close_btn.clicked.connect(self.accept)
        row.addWidget(close_btn)

        layout.addLayout(row)

    def _build_report(self) -> str:
        return (
            f"MADRAC-SUBS v{__version__}\n"
            f"Python {sys.version}\n"
            f"Platform: {platform.platform()}\n"
            f"Frozen: {getattr(sys, 'frozen', False)}\n"
            f"\n---\n{self._details}"
        )

    def _on_copy(self) -> None:
        QApplication.clipboard().setText(self._detail_view.toPlainText())

    def _on_open_log(self) -> None:
        log_path = get_log_path()
        if log_path and log_path.exists():
            import subprocess
            subprocess.Popen(["notepad.exe", str(log_path)])

    def _on_report(self) -> None:
        import webbrowser
        body = textwrap.dedent(f"""\
            ## Error description

            <!-- What were you doing when the error occurred? -->

            ## Details

            ```
            {self._detail_view.toPlainText()}
            ```
        """)
        url = f"https://github.com/anomalyco/madrac-subs/issues/new?body={__import__('urllib').parse.quote(body)}"
        webbrowser.open(url)
