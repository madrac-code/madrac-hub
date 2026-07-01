from pathlib import Path
from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from ...config import get_config, set_config


class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(480, 400)

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        tabs.addTab(self._general_tab(), "General")
        tabs.addTab(self._whisper_tab(), "Whisper")
        tabs.addTab(self._subtitles_tab(), "Subtitles")

        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_row(self, form, label, widget):
        form.addRow(QLabel(label), widget)

    def _general_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setLabelAlignment(Qt.AlignRight)

        self._lang = QComboBox()
        self._lang.addItems(["es", "en", "fr", "de", "it", "pt"])
        self._lang.setCurrentText(get_config("idioma", "es"))
        self._add_row(form, "Language:", self._lang)

        self._out_format = QComboBox()
        self._out_format.addItems(["srt", "vtt", "ass"])
        self._out_format.setCurrentText(get_config("salida.formato", "srt"))
        self._add_row(form, "Output format:", self._out_format)

        out_dir = QHBoxLayout()
        self._out_dir = QLineEdit(get_config("salida.directorio", ""))
        self._out_dir.setPlaceholderText("Same folder as video")
        out_dir.addWidget(self._out_dir)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse_out)
        out_dir.addWidget(browse)
        self._add_row(form, "Output folder:", out_dir)

        notif = QCheckBox()
        notif.setChecked(get_config("gui.notificaciones_sistema", True))
        self._notif = notif
        self._add_row(form, "System notifications:", notif)

        return w

    def _whisper_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setLabelAlignment(Qt.AlignRight)

        self._model = QComboBox()
        self._model.addItems(["tiny", "base", "small", "medium"])
        self._model.setCurrentText(get_config("whisper.modelo", "base"))
        self._add_row(form, "Model:", self._model)

        self._device = QComboBox()
        self._device.addItems(["cpu", "cuda", "auto"])
        self._device.setCurrentText(get_config("whisper.dispositivo", "cpu"))
        self._add_row(form, "Device:", self._device)

        self._compute = QComboBox()
        self._compute.addItems(["int8", "int8_float16", "float16", "float32"])
        self._compute.setCurrentText(get_config("whisper.compute_type", "int8"))
        self._add_row(form, "Compute type:", self._compute)

        self._task = QComboBox()
        self._task.addItems(["transcribe", "translate"])
        self._task.setCurrentText(get_config("whisper.task", "transcribe"))
        self._add_row(form, "Task:", self._task)

        self._beam = QSpinBox()
        self._beam.setRange(1, 20)
        self._beam.setValue(get_config("whisper.beam_size", 5))
        self._add_row(form, "Beam size:", self._beam)

        self._vad = QCheckBox()
        self._vad.setChecked(get_config("whisper.vad_filter", True))
        self._add_row(form, "VAD filter:", self._vad)

        trans = QCheckBox()
        trans.setChecked(get_config("traduccion.habilitada", True))
        self._trans = trans
        self._add_row(form, "Translate:", trans)

        self._tgt_lang = QComboBox()
        self._tgt_lang.addItems(["es", "en", "fr", "de", "it", "pt"])
        self._tgt_lang.setCurrentText(get_config("traduccion.idioma_destino", "es"))
        self._add_row(form, "Target language:", self._tgt_lang)

        return w

    def _subtitles_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setLabelAlignment(Qt.AlignRight)

        self._max_chars = QSpinBox()
        self._max_chars.setRange(20, 100)
        self._max_chars.setValue(get_config("subtitulos.max_chars_por_linea", 42))
        self._add_row(form, "Max chars/line:", self._max_chars)

        self._max_lines = QSpinBox()
        self._max_lines.setRange(1, 4)
        self._max_lines.setValue(get_config("subtitulos.max_lineas_por_subtitulo", 2))
        self._add_row(form, "Max lines/subtitle:", self._max_lines)

        self._min_dur = QSpinBox()
        self._min_dur.setRange(500, 10000)
        self._min_dur.setSuffix(" ms")
        self._min_dur.setValue(get_config("subtitulos.duracion_minima_ms", 1500))
        self._add_row(form, "Min duration:", self._min_dur)

        self._max_dur = QSpinBox()
        self._max_dur.setRange(2000, 30000)
        self._max_dur.setSuffix(" ms")
        self._max_dur.setValue(get_config("subtitulos.duracion_maxima_ms", 7000))
        self._add_row(form, "Max duration:", self._max_dur)

        return w

    def _browse_out(self):
        d = QFileDialog.getExistingDirectory(self, "Output folder", self._out_dir.text())
        if d:
            self._out_dir.setText(d)

    def _save(self):
        set_config("idioma", self._lang.currentText())
        set_config("salida.formato", self._out_format.currentText())
        set_config("salida.directorio", self._out_dir.text().strip())
        set_config("gui.notificaciones_sistema", self._notif.isChecked())
        set_config("whisper.modelo", self._model.currentText())
        set_config("whisper.dispositivo", self._device.currentText())
        set_config("whisper.compute_type", self._compute.currentText())
        set_config("whisper.task", self._task.currentText())
        set_config("whisper.beam_size", self._beam.value())
        set_config("whisper.vad_filter", self._vad.isChecked())
        set_config("traduccion.habilitada", self._trans.isChecked())
        set_config("traduccion.idioma_destino", self._tgt_lang.currentText())
        set_config("subtitulos.max_chars_por_linea", self._max_chars.value())
        set_config("subtitulos.max_lineas_por_subtitulo", self._max_lines.value())
        set_config("subtitulos.duracion_minima_ms", self._min_dur.value())
        set_config("subtitulos.duracion_maxima_ms", self._max_dur.value())
        self.accept()
