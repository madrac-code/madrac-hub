from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

from ... import __version__
from ..i18n import _


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("About MADRAC-SUBS"))
        self.setFixedSize(380, 240)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel(_("MADRAC-SUBS"))
        title.setAlignment(Qt.AlignCenter)
        f = title.font()
        f.setPointSize(18)
        f.setBold(True)
        title.setFont(f)

        version = QLabel(f"{_('Version')} {__version__}")
        version.setAlignment(Qt.AlignCenter)

        desc = QLabel(
            _("Automatic subtitle generation using Whisper\nand machine translation.")
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addSpacing(8)
        layout.addWidget(desc)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton(_("Close"))
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
