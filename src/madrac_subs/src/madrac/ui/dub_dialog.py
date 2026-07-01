"""DubDialog — modal dialog for MADRAC-DUBS configuration and progress."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout,
    QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from ..core import get_logger
from .i18n import _

logger = get_logger("ui.dub_dialog")

_LANGUAGES = [
    ("es", _("Español")),
    ("en", _("Inglés")),
    ("fr", _("Francés")),
    ("pt", _("Portugués")),
    ("de", _("Alemán")),
    ("it", _("Italiano")),
    ("ja", _("Japonés")),
    ("zh", _("Chino")),
]

_VOICES = [
    ("female", _("Femenina")),
    ("male", _("Masculina")),
    ("neutral", _("Neutra")),
]


class DubDialog(QDialog):
    """Two-state dialog: configuration, then progress.

    Signals
    -------
    config_confirmed(config: dict)
        Emitted when the user clicks "Doblar" in config state.
    cancelled()
        Emitted when the user cancels in either state.
    """

    config_confirmed = Signal(dict)
    cancelled = Signal()

    def __init__(self, video_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Doblar video"))
        self.setMinimumWidth(420)
        self.setModal(True)

        self._video_name = video_name
        self._config_widget: QWidget = None
        self._progress_widget: QWidget = None
        self._build_config_state()

    # ------------------------------------------------------------------
    # State: Configuration
    # ------------------------------------------------------------------

    def _build_config_state(self):
        self._clear_content()

        self._config_widget = QWidget()
        layout = QVBoxLayout(self._config_widget)
        layout.setSpacing(12)

        # Header
        header = QLabel(_("Configuración de doblaje"))
        header.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(header)

        subtitle = QLabel(_("Video: {name}").format(name=self._video_name))
        subtitle.setStyleSheet("color: #aaa; margin-bottom: 12px;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Form
        form = QFormLayout()
        form.setSpacing(8)

        self._lang_combo = QComboBox()
        for code, label in _LANGUAGES:
            self._lang_combo.addItem(label, code)
        self._lang_combo.setCurrentIndex(0)
        form.addRow(_("Idioma destino:"), self._lang_combo)

        self._voice_combo = QComboBox()
        for code, label in _VOICES:
            self._voice_combo.addItem(label, code)
        self._voice_combo.setCurrentIndex(0)
        form.addRow(_("Voz:"), self._voice_combo)

        self._vocals_spin = QDoubleSpinBox()
        self._vocals_spin.setRange(0.0, 1.0)
        self._vocals_spin.setSingleStep(0.1)
        self._vocals_spin.setValue(0.3)
        self._vocals_spin.setDecimals(1)
        form.addRow(_("Reducción vocal:"), self._vocals_spin)

        self._high_quality_chk = QCheckBox(_("Alta calidad (Demucs)"))
        self._high_quality_chk.setChecked(False)
        form.addRow("", self._high_quality_chk)

        layout.addLayout(form)
        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton(_("Cancelar"))
        cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(cancel_btn)

        dub_btn = QPushButton(_("Doblar"))
        dub_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; font-weight: bold; "
            "padding: 8px 24px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #2ecc71; }"
        )
        dub_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(dub_btn)

        layout.addLayout(btn_row)

        self._show_widget(self._config_widget)

    # ------------------------------------------------------------------
    # State: Progress
    # ------------------------------------------------------------------

    def _build_progress_state(self):
        self._clear_content()

        self._progress_widget = QWidget()
        layout = QVBoxLayout(self._progress_widget)
        layout.setSpacing(12)

        header = QLabel(_("Doblando video..."))
        header.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFixedHeight(24)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel(_("Iniciando..."))
        self._status_label.setStyleSheet("color: #aaa;")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        layout.addStretch()

        cancel_btn = QPushButton(_("Cancelar"))
        cancel_btn.clicked.connect(self._on_cancel)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self._show_widget(self._progress_widget)

    # ------------------------------------------------------------------
    # Progress updates (called from MainWindow)
    # ------------------------------------------------------------------

    def set_progress(self, pct: int, status: str, message: str):
        self._progress_bar.setValue(pct)
        if message:
            self._status_label.setText(message)

    def set_completed(self):
        self._progress_bar.setValue(100)
        self._status_label.setText(_("¡Doblaje completado!"))

    def set_error(self, error: str):
        self._status_label.setText(_("Error: {msg}").format(msg=error))
        self._status_label.setStyleSheet("color: #f44;")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_confirm(self):
        config = {
            "language": self._lang_combo.currentData(),
            "voice": self._voice_combo.currentData(),
            "reduce_vocals": self._vocals_spin.value(),
            "high_quality": self._high_quality_chk.isChecked(),
        }
        self._build_progress_state()
        self.config_confirmed.emit(config)

    def _on_cancel(self):
        self.cancelled.emit()
        self.reject()

    def _clear_content(self):
        self._config_widget = None
        self._progress_widget = None
        # Remove all children from the layout
        while self.layout() is not None:
            old = self.layout()
            QWidget().setLayout(old)

    def _show_widget(self, widget):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(widget)
