"""Extensions dialog — multi-tab settings replacing ConfigDialog."""

import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QSpinBox, QTabWidget,
    QVBoxLayout, QWidget,
)

from ...config import get_config, set_config
from .disk_space_panel import DiskSpacePanel
from ..i18n import _


class ExtensionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Extensiones"))
        self.setMinimumSize(520, 460)

        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._general_tab(), _("General"))
        self._tabs.addTab(self._comunidad_tab(), _("Comunidad"))
        self._tabs.addTab(self._processing_tab(), _("Procesamiento"))
        self._tabs.addTab(self._storage_tab(), _("Almacenamiento"))
        self._tabs.addTab(self._plugins_tab(), _("Plugins"))

        self._advanced_tab = self._advanced_tab()
        self._tabs.addTab(self._advanced_tab, _("Avanzado"))

        layout.addWidget(self._tabs)

        self._show_advanced = QPushButton(_("Mostrar opciones avanzadas"))
        self._show_advanced.setStyleSheet("color: #888; font-size: 9pt; border: none; text-decoration: underline;")
        self._show_advanced.clicked.connect(self._toggle_advanced)
        layout.addWidget(self._show_advanced, alignment=Qt.AlignRight)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Initially hide the Avanzado tab
        self._advanced_hidden = True
        self._tabs.removeTab(4)

    def _toggle_advanced(self):
        if self._advanced_hidden:
            self._tabs.insertTab(4, self._advanced_tab, _("Avanzado"))
            self._show_advanced.setText(_("Ocultar opciones avanzadas"))
            self._advanced_hidden = False
        else:
            self._tabs.removeTab(4)
            self._show_advanced.setText(_("Mostrar opciones avanzadas"))
            self._advanced_hidden = True

    def _add_row(self, form, label, widget):
        form.addRow(QLabel(label), widget)

    # ── General tab ─────────────────────────────────────────────────

    def _general_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setLabelAlignment(Qt.AlignRight)

        self._lang = QComboBox()
        self._lang.addItems(["es", "en", "fr", "de", "it", "pt"])
        self._lang.setCurrentText(get_config("idioma", "es"))
        self._add_row(form, _("Idioma:"), self._lang)

        self._out_format = QComboBox()
        self._out_format.addItems(["srt", "vtt", "ass"])
        self._out_format.setCurrentText(get_config("salida.formato", "srt"))
        self._add_row(form, _("Formato salida:"), self._out_format)

        out_dir = QHBoxLayout()
        self._out_dir = QLineEdit(get_config("salida.directorio", ""))
        self._out_dir.setPlaceholderText(_("Misma carpeta que el video"))
        out_dir.addWidget(self._out_dir)
        browse = QPushButton("...")
        browse.clicked.connect(self._browse_out)
        out_dir.addWidget(browse)
        self._add_row(form, _("Carpeta salida:"), out_dir)

        self._notif = QCheckBox()
        self._notif.setChecked(get_config("gui.notificaciones_sistema", True))
        self._add_row(form, _("Notificaciones:"), self._notif)

        return w

    def _browse_out(self):
        d = QFileDialog.getExistingDirectory(self, _("Carpeta salida:"), self._out_dir.text())
        if d:
            self._out_dir.setText(d)

    # ── Comunidad tab ────────────────────────────────────────────────

    def _comunidad_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setLabelAlignment(Qt.AlignRight)

        self._habilitado = QCheckBox()
        self._habilitado.setChecked(get_config("comunidad.habilitado", True))
        self._add_row(form, _("Habilitar comunidad:"), self._habilitado)

        self._auto_subir = QCheckBox()
        self._auto_subir.setChecked(get_config("comunidad.subir_automaticamente", True))
        self._add_row(form, _("Compartir subtitulos:"), self._auto_subir)

        self._share_consent = QCheckBox()
        self._share_consent.setChecked(get_config("comunidad.share_consent_given", False))
        self._add_row(form, _("Compartir metadatos:"), self._share_consent)

        self._normalizacion = QCheckBox()
        self._normalizacion.setChecked(get_config("comunidad.normalizacion_habilitada", True))
        self._add_row(form, _("Extraer metadatos:"), self._normalizacion)

        info = QLabel(
            "<br>"
            f"<b>{_('Compartir subtitulos:')}</b> {_('envia los SRT generados a la comunidad')}<br>"
            f"<b>{_('Compartir metadatos:')}</b> {_('adjunta informacion del video a los subtitulos compartidos')}<br>"
            f"<b>{_('Extraer metadatos:')}</b> {_('analiza nombre y video localmente (temporada, resolucion, codec)')}"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #888; font-size: 9pt;")
        form.addRow(info)

        return w

    # ── Language→engine overrides ───────────────────────────────────

    _KNOWN_LANGUAGES = [
        ("ja", "Japonés"),
        ("zh", "Chino"),
        ("ko", "Coreano"),
        ("ar", "Árabe"),
        ("he", "Hebreo"),
        ("hi", "Hindi"),
        ("th", "Tailandés"),
        ("vi", "Vietnamita"),
        ("nn", "Noruego (Nynorsk)"),
        ("nb", "Noruego (Bokmål)"),
        ("nl", "Neerlandés"),
        ("de", "Alemán"),
        ("fr", "Francés"),
        ("it", "Italiano"),
        ("pt", "Portugués"),
        ("ru", "Ruso"),
    ]
    _ENGINE_OPTIONS = ["", "marianmt", "gemini", "libretranslate", "google"]
    _ENGINE_LABELS = {
        "": "Por defecto",
        "marianmt": "MarianMT",
        "gemini": "Gemini",
        "libretranslate": "LibreTranslate",
        "google": "Google Translate",
    }

    # ── Processing tab ───────────────────────────────────────────────

    def _processing_tab(self):
        w = QWidget()
        outer = QVBoxLayout(w)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)

        # ── Main settings form ──
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self._model = QComboBox()
        self._model.addItems(["tiny", "base", "small", "medium"])
        self._model.setCurrentText(get_config("whisper.modelo", "base"))
        form.addRow(QLabel(_("Modelo:")), self._model)

        self._device = QComboBox()
        self._device.addItems(["auto", "cpu", "cuda"])
        self._device.setCurrentText(get_config("whisper.dispositivo", "auto"))
        form.addRow(QLabel(_("Dispositivo:")), self._device)

        self._task = QComboBox()
        self._task.addItems(["transcribe", "translate"])
        self._task.setCurrentText(get_config("whisper.task", "transcribe"))
        form.addRow(QLabel(_("Tarea:")), self._task)

        self._vad = QCheckBox()
        self._vad.setChecked(get_config("whisper.vad_filter", True))
        form.addRow(QLabel(_("Filtro VAD:")), self._vad)

        self._trans = QCheckBox()
        self._trans.setChecked(get_config("traduccion.habilitada", True))
        form.addRow(QLabel(_("Traducir:")), self._trans)

        self._main_engine = QComboBox()
        self._main_engine.addItems(["marianmt", "gemini", "libretranslate", "google"])
        self._main_engine.setCurrentText(get_config("traduccion.motor", "marianmt"))
        form.addRow(QLabel(_("Motor principal:")), self._main_engine)

        self._tgt_lang = QComboBox()
        self._tgt_lang.addItems(["es", "en", "fr", "de", "it", "pt"])
        self._tgt_lang.setCurrentText(get_config("traduccion.idioma_destino", "es"))
        form.addRow(QLabel(_("Idioma destino:")), self._tgt_lang)

        layout.addLayout(form)

        # ── Language→engine overrides ──
        layout.addSpacing(8)
        group = QGroupBox(_("Traductores por idioma"))
        group.setStyleSheet("QGroupBox { font-weight: bold; }")
        group_layout = QVBoxLayout(group)

        info = QLabel(
            _("Selecciona que motor usar para cada idioma.\nPor defecto se usa el motor principal.")
        )
        info.setStyleSheet("color: #888; font-size: 9pt;")
        info.setWordWrap(True)
        group_layout.addWidget(info)

        scroll_table = QScrollArea()
        scroll_table.setWidgetResizable(True)
        scroll_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_table.setMaximumHeight(200)
        scroll_inner = QWidget()
        scroll_form = QFormLayout(scroll_inner)
        scroll_form.setLabelAlignment(Qt.AlignRight)
        scroll_form.setContentsMargins(4, 4, 4, 4)

        self._lang_overrides = {}
        motor_por_idioma = get_config("traduccion.motor_por_idioma", {})
        for code, name in self._KNOWN_LANGUAGES:
            cb = QComboBox()
            for opt in self._ENGINE_OPTIONS:
                cb.addItem(self._ENGINE_LABELS[opt], opt)
            current_override = motor_por_idioma.get(code, "")
            idx = cb.findData(current_override)
            if idx >= 0:
                cb.setCurrentIndex(idx)
            scroll_form.addRow(QLabel(f"{name} ({code}):"), cb)
            self._lang_overrides[code] = cb

        scroll_table.setWidget(scroll_inner)
        group_layout.addWidget(scroll_table)
        layout.addWidget(group)

        # ── Engine configuration ──
        layout.addSpacing(8)
        eng_group = QGroupBox(_("Configuracion de motores"))
        eng_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        eng_layout = QVBoxLayout(eng_group)

        # -- Gemini --
        gem_form = QFormLayout()
        gem_form.setLabelAlignment(Qt.AlignRight)

        self._gem_api_key = QLineEdit()
        self._gem_api_key.setEchoMode(QLineEdit.Password)
        self._gem_api_key.setText(get_config("motores_traduccion.gemini.api_key", ""))
        self._gem_api_key.setPlaceholderText("AIza...")
        gem_form.addRow(QLabel(_("Gemini API Key:")), self._gem_api_key)

        self._gem_modelo = QComboBox()
        self._gem_modelo.addItems(["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro", "gemini-3.5-flash"])
        self._gem_modelo.setCurrentText(get_config("motores_traduccion.gemini.modelo", "gemini-2.5-flash"))
        gem_form.addRow(QLabel(_("Gemini modelo:")), self._gem_modelo)

        self._gem_install_btn = QPushButton()
        self._gem_install_btn.setStyleSheet("font-size: 9pt;")
        if getattr(sys, "frozen", False):
            self._gem_install_btn.setText(_("Ya incluido en el paquete"))
            self._gem_install_btn.setEnabled(False)
        else:
            self._gem_install_btn.setText(_("Instalar Gemini (pip install)"))
            self._gem_install_btn.clicked.connect(self._on_install_gemini)
        gem_form.addRow(QLabel(""), self._gem_install_btn)

        gem_w = QWidget()
        gem_w.setLayout(gem_form)
        eng_layout.addWidget(gem_w)

        # -- LibreTranslate --
        lt_form = QFormLayout()
        lt_form.setLabelAlignment(Qt.AlignRight)

        self._lt_url = QLineEdit()
        self._lt_url.setText(get_config("motores_traduccion.libretranslate.url", "http://localhost:5000"))
        lt_form.addRow(QLabel(_("LibreTranslate URL:")), self._lt_url)

        self._lt_api_key = QLineEdit()
        self._lt_api_key.setEchoMode(QLineEdit.Password)
        self._lt_api_key.setText(get_config("motores_traduccion.libretranslate.api_key", ""))
        lt_form.addRow(QLabel(_("LibreTranslate API Key:")), self._lt_api_key)

        self._lt_timeout = QSpinBox()
        self._lt_timeout.setRange(5, 120)
        self._lt_timeout.setValue(get_config("motores_traduccion.libretranslate.timeout", 30))
        self._lt_timeout.setSuffix(" s")
        lt_form.addRow(QLabel(_("Timeout:")), self._lt_timeout)

        lt_w = QWidget()
        lt_w.setLayout(lt_form)
        eng_layout.addWidget(lt_w)

        # -- Google Translate --
        gt_form = QFormLayout()
        gt_form.setLabelAlignment(Qt.AlignRight)

        self._gt_timeout = QSpinBox()
        self._gt_timeout.setRange(5, 120)
        self._gt_timeout.setValue(get_config("motores_traduccion.google.timeout", 30))
        self._gt_timeout.setSuffix(" s")
        gt_form.addRow(QLabel(_("Google timeout:")), self._gt_timeout)

        gt_w = QWidget()
        gt_w.setLayout(gt_form)
        eng_layout.addWidget(gt_w)

        layout.addWidget(eng_group)
        layout.addStretch()

        scroll.setWidget(inner)
        outer.addWidget(scroll)
        return w

    # ── Storage tab ──────────────────────────────────────────────────

    def _storage_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        self._disk_panel = DiskSpacePanel()
        layout.addWidget(self._disk_panel)

        layout.addSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        cache_dir = QHBoxLayout()
        self._cache_dir = QLineEdit(get_config("directorios.cache_modelos", ""))
        self._cache_dir.setPlaceholderText(_("Por defecto: ~/.cache/huggingface"))
        cache_dir.addWidget(self._cache_dir)
        browse_cache = QPushButton("...")
        browse_cache.clicked.connect(lambda: self._browse_dir(self._cache_dir))
        cache_dir.addWidget(browse_cache)
        form.addRow(QLabel(_("Cache modelos:")), cache_dir)

        temp_dir = QHBoxLayout()
        self._temp_dir = QLineEdit(get_config("directorios.temporal", ""))
        self._temp_dir.setPlaceholderText(_("Por defecto: temp del sistema"))
        temp_dir.addWidget(self._temp_dir)
        browse_temp = QPushButton("...")
        browse_temp.clicked.connect(lambda: self._browse_dir(self._temp_dir))
        temp_dir.addWidget(browse_temp)
        form.addRow(QLabel(_("Temp:")), temp_dir)

        self._cleanup = QCheckBox()
        self._cleanup.setChecked(get_config("procesamiento.limpiar_cache_temporal", True))
        form.addRow(QLabel(_("Limpiar al terminar:")), self._cleanup)

        layout.addLayout(form)
        layout.addStretch()

        return w

    def _browse_dir(self, field: QLineEdit):
        d = QFileDialog.getExistingDirectory(self, _("Seleccionar directorio"), field.text())
        if d:
            field.setText(d)

    # ── Plugins tab ──────────────────────────────────────────────────

    def _plugins_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        lbl = QLabel(_("Extensiones y plugins instalados:"))
        layout.addWidget(lbl)

        active = get_config("plugins.active", [])
        if active:
            for p in active:
                layout.addWidget(QLabel(f"  \u2022 {p}"))
        else:
            layout.addWidget(QLabel(_("  (ninguno)")))

        layout.addSpacing(12)

        reg = get_config("file_handlers.registered", False)
        status = _("Registrado") if reg else _("No registrado")
        color = "green" if reg else "#888"
        self._fh_label = QLabel(f'<b style="color:{color};">{_("Integracion Windows")}: {status}</b>')
        self._fh_label.setOpenExternalLinks(False)
        layout.addWidget(self._fh_label)

        if not reg:
            info = QLabel(
                _("La integracion se ejecuta automaticamente al iniciar si no esta registrada.")
            )
            info.setStyleSheet("color: #888; font-size: 9pt;")
            layout.addWidget(info)

        layout.addSpacing(16)

        reset_btn = QPushButton(_("Restablecer asistente de configuracion"))
        reset_btn.setStyleSheet("color: #e67e22;")
        reset_btn.clicked.connect(self._on_reset_wizard)
        layout.addWidget(reset_btn)

        layout.addStretch()
        return w

    def _on_reset_wizard(self):
        ret = QMessageBox.question(
            self,
            _("Restablecer asistente"),
            _("Esto marcara la configuracion como incompleta.\nEl asistente se mostrara al reiniciar la aplicacion.\n\nContinuar?"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret == QMessageBox.Yes:
            set_config("setup_completed", False)
            QMessageBox.information(
                self, _("Listo"),
                _("Asistente restablecido. Reinicia la aplicacion para verlo.")
            )

    def _on_install_gemini(self):
        ret = QMessageBox.question(
            self,
            _("Instalar Gemini"),
            _("Se instalara el paquete 'google-genai' via pip.\n\nContinuar?"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return

        self._gem_install_btn.setEnabled(False)
        self._gem_install_btn.setText(_("Instalando..."))
        QMessageBox.information(
            self, _("Instalando"),
            _("La instalacion comenzara en segundo plano.\nPuede tardar unos segundos.")
        )

        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pip", "install", "google-genai"],
                capture_output=True, text=True, timeout=120,
            )
            if proc.returncode == 0:
                self._gem_install_btn.setText(_("Instalado correctamente"))
                self._gem_install_btn.setStyleSheet("color: green; font-size: 9pt;")
                QMessageBox.information(
                    self, _("Listo"),
                    _("google-genai instalado correctamente.\nReinicia la aplicacion para usarlo.")
                )
            else:
                self._gem_install_btn.setText(_("Error al instalar"))
                self._gem_install_btn.setEnabled(True)
                QMessageBox.warning(
                    self, _("Error"),
                    f"{_('pip install fallo')}:\n{proc.stderr[:500]}"
                )
        except subprocess.TimeoutExpired:
            self._gem_install_btn.setText(_("Timeout"))
            self._gem_install_btn.setEnabled(True)
            QMessageBox.warning(self, _("Error"), _("La instalacion excedio los 120s."))
        except Exception as e:
            self._gem_install_btn.setText(_("Error"))
            self._gem_install_btn.setEnabled(True)
            QMessageBox.warning(self, _("Error"), str(e)[:300])

    # ── Advanced tab ─────────────────────────────────────────────────

    def _advanced_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setLabelAlignment(Qt.AlignRight)

        self._compute = QComboBox()
        self._compute.addItems(["int8", "int8_float16", "float16", "float32"])
        self._compute.setCurrentText(get_config("whisper.compute_type", "int8"))
        self._add_row(form, _("Computo:"), self._compute)

        self._beam = QSpinBox()
        self._beam.setRange(1, 20)
        self._beam.setValue(get_config("whisper.beam_size", 5))
        self._add_row(form, _("Beam size:"), self._beam)

        self._threads = QSpinBox()
        self._threads.setRange(0, 64)
        self._threads.setSpecialValueText("Auto")
        self._threads.setValue(get_config("whisper.thread_count", 0))
        self._add_row(form, _("Hilos:"), self._threads)

        self._parallel = QCheckBox()
        self._parallel.setChecked(get_config("procesamiento.procesamiento_paralelo", False))
        self._add_row(form, _("Paralelo:"), self._parallel)

        self._max_workers = QSpinBox()
        self._max_workers.setRange(1, 8)
        self._max_workers.setValue(get_config("procesamiento.max_workers", 1))
        self._add_row(form, _("Max workers:"), self._max_workers)

        return w

    # ── Save ─────────────────────────────────────────────────────────

    def _save(self):
        set_config("idioma", self._lang.currentText())
        from ..i18n import setup as i18n_setup
        i18n_setup(self._lang.currentText())
        set_config("salida.formato", self._out_format.currentText())
        set_config("salida.directorio", self._out_dir.text().strip())
        set_config("gui.notificaciones_sistema", self._notif.isChecked())

        set_config("comunidad.habilitado", self._habilitado.isChecked())
        set_config("comunidad.subir_automaticamente", self._auto_subir.isChecked())
        set_config("comunidad.share_consent_given", self._share_consent.isChecked())
        set_config("comunidad.normalizacion_habilitada", self._normalizacion.isChecked())

        set_config("whisper.modelo", self._model.currentText())
        set_config("whisper.dispositivo", self._device.currentText())
        set_config("whisper.task", self._task.currentText())
        set_config("whisper.vad_filter", self._vad.isChecked())
        set_config("traduccion.habilitada", self._trans.isChecked())
        set_config("traduccion.motor", self._main_engine.currentText())
        set_config("traduccion.idioma_destino", self._tgt_lang.currentText())
        overrides = {}
        for code, cb in self._lang_overrides.items():
            val = cb.currentData()
            if val:
                overrides[code] = val
        set_config("traduccion.motor_por_idioma", overrides)

        set_config("motores_traduccion.gemini.api_key", self._gem_api_key.text().strip())
        set_config("motores_traduccion.gemini.modelo", self._gem_modelo.currentText())
        lt_url = self._lt_url.text().strip().rstrip("/")
        if "/translate" in lt_url:
            lt_url = lt_url.split("/translate")[0].rstrip("/")
        set_config("motores_traduccion.libretranslate.url", lt_url)
        set_config("motores_traduccion.libretranslate.api_key", self._lt_api_key.text().strip())
        set_config("motores_traduccion.libretranslate.timeout", self._lt_timeout.value())
        set_config("motores_traduccion.google.timeout", self._gt_timeout.value())

        set_config("directorios.cache_modelos", self._cache_dir.text().strip())
        set_config("directorios.temporal", self._temp_dir.text().strip())
        set_config("procesamiento.limpiar_cache_temporal", self._cleanup.isChecked())

        if not self._advanced_hidden:
            set_config("whisper.compute_type", self._compute.currentText())
            set_config("whisper.beam_size", self._beam.value())
            set_config("whisper.thread_count", self._threads.value())
            set_config("procesamiento.procesamiento_paralelo", self._parallel.isChecked())
            set_config("procesamiento.max_workers", self._max_workers.value())

        self.accept()
