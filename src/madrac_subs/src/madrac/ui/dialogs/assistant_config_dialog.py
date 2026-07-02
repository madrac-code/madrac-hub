from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSlider, QSpinBox, QTabWidget,
    QVBoxLayout, QWidget,
)

from ...assistant.config import load_config, save_config
from ..i18n import _


class AssistantConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Configuración del Asistente"))
        self.setMinimumSize(500, 400)
        self.setModal(False)
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        tabs.addTab(self._general_tab(), _("General"))
        tabs.addTab(self._audio_tab(), _("Audio"))
        tabs.addTab(self._features_tab(), _("Funcionalidades"))

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._save_btn = QPushButton(_("Guardar"))
        self._save_btn.clicked.connect(self._save)
        btn_row.addWidget(self._save_btn)
        self._close_btn = QPushButton(_("Cerrar"))
        self._close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._close_btn)
        layout.addLayout(btn_row)

    def _general_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self._ollama_model = QLineEdit()
        self._ollama_model.setPlaceholderText("llama3.2:latest")
        form.addRow(_("Modelo Ollama:"), self._ollama_model)

        self._ollama_url = QLineEdit()
        self._ollama_url.setPlaceholderText("http://127.0.0.1:11434")
        form.addRow(_("URL Ollama:"), self._ollama_url)

        self._wake_word = QLineEdit()
        self._wake_word.setPlaceholderText("jarvis")
        form.addRow(_("Palabra de activación:"), self._wake_word)

        self._language = QComboBox()
        self._language.addItems(["es", "en", "fr", "pt", "de", "it"])
        form.addRow(_("Idioma:"), self._language)
        return tab

    def _audio_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self._device = QComboBox()
        self._device.setEditable(True)
        self._device.addItem("")
        form.addRow(_("Dispositivo micrófono:"), self._device)

        self._sample_rate = QSpinBox()
        self._sample_rate.setRange(8000, 48000)
        self._sample_rate.setValue(16000)
        self._sample_rate.setSingleStep(1000)
        form.addRow(_("Sample rate:"), self._sample_rate)

        self._record_secs = QSpinBox()
        self._record_secs.setRange(1, 30)
        self._record_secs.setValue(5)
        form.addRow(_("Duración grabación (s):"), self._record_secs)

        self._volume = QSlider(Qt.Horizontal)
        self._volume.setRange(0, 100)
        self._volume.setValue(80)
        form.addRow(_("Volumen:"), self._volume)
        return tab

    def _features_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        self._voice = QCheckBox(_("Activar voz"))
        self._voice.setChecked(True)
        form.addRow(self._voice)

        self._auto_click = QCheckBox(_("Click automático"))
        self._auto_click.setEnabled(False)
        lbl1 = QLabel(_("(Disponible en próxima fase)"))
        lbl1.setStyleSheet("color: #888; font-style: italic;")
        form.addRow(self._auto_click, lbl1)

        self._clipboard = QCheckBox(_("Supervisar portapapeles"))
        self._clipboard.setEnabled(False)
        lbl2 = QLabel(_("(Disponible en próxima fase)"))
        lbl2.setStyleSheet("color: #888; font-style: italic;")
        form.addRow(self._clipboard, lbl2)

        self._takeover = QCheckBox(_("Control total del sistema"))
        self._takeover.setEnabled(False)
        lbl3 = QLabel(_("(Disponible en próxima fase)"))
        lbl3.setStyleSheet("color: #888; font-style: italic;")
        form.addRow(self._takeover, lbl3)
        return tab

    def _load(self):
        cfg = load_config()
        self._ollama_model.setText(cfg.get("modelo", ""))
        self._ollama_url.setText(cfg.get("url", ""))
        self._wake_word.setText(cfg.get("wakeword", {}).get("keyword", ""))
        self._language.setCurrentText(cfg.get("idioma", "es"))
        audio = cfg.get("audio", {})
        self._sample_rate.setValue(audio.get("sample_rate", 16000))
        self._record_secs.setValue(audio.get("duracion_grabacion", 5))
        self._volume.setValue(audio.get("volumen", 80))
        device = audio.get("dispositivo_mic", "")
        self._device.setEditText(str(device) if device else "")
        self._voice.setChecked(cfg.get("voz", True))
        import sounddevice as sd
        devices = sd.query_devices()
        current = self._device.currentText()
        self._device.clear()
        for d in devices:
            name = d["name"]
            self._device.addItem(f"{name} (ID {d['index']})")
            if current and (current in name or current in d["name"]):
                self._device.setCurrentText(f"{name} (ID {d['index']})")

    def _save(self):
        cfg = load_config()
        cfg["modelo"] = self._ollama_model.text()
        cfg["url"] = self._ollama_url.text()
        cfg["idioma"] = self._language.currentText()
        cfg.setdefault("wakeword", {})["keyword"] = self._wake_word.text()
        cfg.setdefault("wakeword", {})["modelo"] = cfg.get("wakeword", {}).get("modelo", "")
        audio = cfg.setdefault("audio", {})
        audio["sample_rate"] = self._sample_rate.value()
        audio["duracion_grabacion"] = self._record_secs.value()
        audio["volumen"] = self._volume.value()
        device_text = self._device.currentText()
        if " (ID " in device_text:
            audio["dispositivo_mic"] = int(device_text.split("(ID ")[1].rstrip(")"))
        else:
            audio["dispositivo_mic"] = device_text or ""
        cfg["voz"] = self._voice.isChecked()
        save_config(cfg)
