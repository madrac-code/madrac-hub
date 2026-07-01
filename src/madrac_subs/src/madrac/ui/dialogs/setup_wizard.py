"""First-run setup wizard for MADRAC-SUBS v3."""

import shutil
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QFileDialog, QWizard, QWizardPage,
    QFormLayout, QGroupBox, QRadioButton, QTextEdit,
)

from ...core.paths import get_user_config_dir, get_temp_dir
from ...core.logging import get_logger
from ...utils.ffmpeg import resolve_executable
from ... import __version__
from ..i18n import _

logger = get_logger("ui.setup_wizard")

_LANGS = [
    ("es", "Espanol"),
    ("en", "English"),
    ("fr", "Francais"),
    ("pt", "Portugues"),
    ("de", "Deutsch"),
    ("it", "Italiano"),
    ("ja", "Nihongo"),
    ("zh", "Chino"),
]

_MODELS = [
    ("tiny", "Tiny (rapido, menos preciso)"),
    ("base", "Base (recomendado)"),
    ("small", "Small (equilibrado)"),
    ("medium", "Medium (lento, preciso)"),
]


_TERMS_TEXT = """\
MADRAC-SUBS es una herramienta de subtitulado automatico que recopila
datos anonimizados para mejorar la experiencia colectiva.

Al aceptar los terminos, contribuyes con:

  - Subtitulos generados (archivos SRT)
  - Metadatos del video (nombre, resolucion, codec, duracion, etc.)
  - Estadisticas de procesamiento (modelo, tiempo real, dispositivo)

No se comparte informacion personal identificable.
Los datos se almacenan de forma anonima y segura.

Puedes desactivar o ajustar la participacion comunitaria en cualquier
momento desde Extensiones > Comunidad.
"""


class _FirstPage(QWizardPage):
    """Combined welcome, language, terms, and community consent."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Bienvenido a MADRAC-SUBS")
        self.setSubTitle("Configuracion inicial y participacion comunitaria")

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._lang_combo = QComboBox()
        from ..i18n import detect_system_language
        _sys_lang = detect_system_language()
        _selected_idx = 0
        for i, (code, name) in enumerate(_LANGS):
            self._lang_combo.addItem(f"{name} ({code})", code)
            if code == _sys_lang:
                _selected_idx = i
        self._lang_combo.setCurrentIndex(_selected_idx)
        form.addRow(_("Idioma:"), self._lang_combo)
        layout.addLayout(form)

        layout.addSpacing(12)

        section = QLabel(_("Participacion comunitaria"))
        section.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(section)

        terms = QTextEdit()
        terms.setReadOnly(True)
        terms.setPlainText(_TERMS_TEXT)
        terms.setMaximumHeight(140)
        layout.addWidget(terms)

        self._terms_cb = QCheckBox(_("Acepto los terminos y condiciones"))
        self._terms_cb.toggled.connect(self._on_terms_toggled)
        layout.addWidget(self._terms_cb)

        layout.addSpacing(8)

        self._subir_cb = QCheckBox(_("Compartir subtitulos con la comunidad (recomendado)"))
        self._subir_cb.setChecked(True)
        self._subir_cb.setEnabled(False)
        layout.addWidget(self._subir_cb)

        self._extraer_cb = QCheckBox(_("Extraer metadatos del video (temporada, resolucion, codec)"))
        self._extraer_cb.setChecked(True)
        self._extraer_cb.setEnabled(False)
        layout.addWidget(self._extraer_cb)

        self._compartir_meta_cb = QCheckBox(_("Compartir metadatos con la comunidad"))
        self._compartir_meta_cb.setChecked(False)
        self._compartir_meta_cb.setEnabled(False)
        layout.addWidget(self._compartir_meta_cb)

        layout.addSpacing(8)

        info = QLabel(_("Puedes cambiar estas opciones despues en Extensiones > Comunidad."))
        info.setStyleSheet("color: #888; font-size: 9pt;")
        layout.addWidget(info)

        layout.addStretch()

    def _on_terms_toggled(self, checked: bool) -> None:
        self._subir_cb.setEnabled(checked)
        self._extraer_cb.setEnabled(checked)
        self._compartir_meta_cb.setEnabled(checked)

    def selected_language(self) -> str:
        return self._lang_combo.currentData()

    def get_community_config(self) -> dict:
        accepted = self._terms_cb.isChecked()
        return {
            "habilitado": accepted,
            "subir_automaticamente": accepted and self._subir_cb.isChecked(),
            "normalizacion_habilitada": accepted and self._extraer_cb.isChecked(),
            "share_consent_given": accepted and self._compartir_meta_cb.isChecked(),
        }


class _FfmpegPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle(_("FFmpeg"))
        self.setSubTitle(_("Deteccion de FFmpeg y FFprobe"))

        layout = QVBoxLayout(self)

        self._ffmpeg_status = QLabel(_("Buscando FFmpeg..."))
        self._ffmpeg_status.setStyleSheet("padding: 4px 0;")
        layout.addWidget(self._ffmpeg_status)

        self._ffprobe_status = QLabel(_("Buscando FFprobe..."))
        self._ffprobe_status.setStyleSheet("padding: 4px 0;")
        layout.addWidget(self._ffprobe_status)

        layout.addSpacing(8)

        self._manual_group = QGroupBox(_("Ruta manual (opcional)"))
        manual_layout = QHBoxLayout(self._manual_group)
        self._ffmpeg_path = QLineEdit()
        self._ffmpeg_path.setPlaceholderText(_("Ruta a ffmpeg.exe"))
        manual_layout.addWidget(self._ffmpeg_path)
        browse_btn = QPushButton(_("..."))
        browse_btn.clicked.connect(self._on_browse)
        manual_layout.addWidget(browse_btn)
        layout.addWidget(self._manual_group)

        layout.addStretch()

        self._ffmpeg_ok = False
        self._ffprobe_ok = False
        self._checked = False

    def initializePage(self):
        if not self._checked:
            self._check()

    def _on_browse(self):
        path, _filt = QFileDialog.getOpenFileName(
            self, _("Seleccionar ffmpeg"), "",
            "ffmpeg (ffmpeg.exe);;Todos (*.*)",
        )
        if path:
            self._ffmpeg_path.setText(path)
            self._check()

    def _check(self):
        self._checked = True
        ffmpeg = self._ffmpeg_path.text().strip() or resolve_executable("ffmpeg")
        ffprobe = resolve_executable("ffprobe")

        if ffmpeg:
            self._ffmpeg_status.setText(f"FFmpeg: {ffmpeg}")
            self._ffmpeg_status.setStyleSheet("color: green; padding: 4px 0;")
            self._ffmpeg_ok = True
        else:
            self._ffmpeg_status.setText(_("FFmpeg: NO ENCONTRADO"))
            self._ffmpeg_status.setStyleSheet("color: red; padding: 4px 0;")
            self._ffmpeg_ok = False

        if ffprobe:
            self._ffprobe_status.setText(f"FFprobe: {ffprobe}")
            self._ffprobe_status.setStyleSheet("color: green; padding: 4px 0;")
            self._ffprobe_ok = True
        else:
            self._ffprobe_status.setText(_("FFprobe: NO ENCONTRADO"))
            self._ffprobe_status.setStyleSheet("color: red; padding: 4px 0;")
            self._ffprobe_ok = False

        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self._ffmpeg_ok and self._ffprobe_ok

    def ffmpeg_path(self) -> str:
        return self._ffmpeg_path.text().strip() or (resolve_executable("ffmpeg") or "")

    def ffprobe_path(self) -> str:
        return resolve_executable("ffprobe") or ""


class _ModelPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle(_("Modelo Whisper"))
        self.setSubTitle(_("Selecciona el modelo de transcripcion"))

        layout = QVBoxLayout(self)

        label = QLabel(
            _("Los modelos mas grandes ofrecen mejor precision\npero requieren mas RAM/VRAM y tiempo de procesamiento.")
        )
        label.setWordWrap(True)
        layout.addWidget(label)

        layout.addSpacing(8)

        self._model_combo = QComboBox()
        for key, desc in _MODELS:
            self._model_combo.addItem(_(desc), key)
        self._model_combo.setCurrentIndex(1)
        layout.addWidget(self._model_combo)

        layout.addSpacing(12)

        cache_group = QGroupBox(_("Directorio de cache"))
        cache_layout = QHBoxLayout(cache_group)
        self._cache_path = QLineEdit(str(get_user_config_dir() / "models"))
        cache_layout.addWidget(self._cache_path)
        browse_btn = QPushButton(_("..."))
        browse_btn.clicked.connect(self._on_browse_cache)
        cache_layout.addWidget(browse_btn)
        layout.addWidget(cache_group)

        layout.addStretch()

    def _on_browse_cache(self):
        path = QFileDialog.getExistingDirectory(self, _("Directorio de cache"))
        if path:
            self._cache_path.setText(path)

    def selected_model(self) -> str:
        return self._model_combo.currentData()

    def cache_dir(self) -> str:
        return self._cache_path.text().strip()


class _DirectoriesPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle(_("Directorios"))
        self.setSubTitle(_("Configuracion de carpetas"))

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self._output_dir = QLineEdit()
        self._output_dir.setPlaceholderText(_("Directorio de salida (vacio = junto al video)"))
        browse_out = QPushButton(_("..."))
        browse_out.clicked.connect(lambda: self._browse(self._output_dir))
        out_row = QHBoxLayout()
        out_row.addWidget(self._output_dir)
        out_row.addWidget(browse_out)
        form.addRow(_("Salida:"), out_row)

        self._temp_dir = QLineEdit(str(get_temp_dir()))
        browse_temp = QPushButton(_("..."))
        browse_temp.clicked.connect(lambda: self._browse(self._temp_dir))
        temp_row = QHBoxLayout()
        temp_row.addWidget(self._temp_dir)
        temp_row.addWidget(browse_temp)
        form.addRow(_("Temporal:"), temp_row)

        layout.addLayout(form)

        layout.addSpacing(12)

        self._cleanup_cb = QCheckBox(_("Limpiar archivos temporales al completar"))
        self._cleanup_cb.setChecked(True)
        layout.addWidget(self._cleanup_cb)

        self._notif_cb = QCheckBox(_("Mostrar notificaciones del sistema"))
        self._notif_cb.setChecked(True)
        layout.addWidget(self._notif_cb)

        layout.addStretch()

    def _browse(self, field: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, _("Seleccionar directorio"))
        if path:
            field.setText(path)

    def output_dir(self) -> str:
        return self._output_dir.text().strip()

    def temp_dir(self) -> str:
        return self._temp_dir.text().strip()

    def cleanup(self) -> bool:
        return self._cleanup_cb.isChecked()

    def notifications(self) -> bool:
        return self._notif_cb.isChecked()


class SetupWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Asistente de configuracion — MADRAC-SUBS"))
        self.setMinimumSize(520, 400)
        self.setWizardStyle(QWizard.ModernStyle)

        self._welcome = _FirstPage(self)
        self._ffmpeg = _FfmpegPage(self)
        self._model = _ModelPage(self)
        self._dirs = _DirectoriesPage(self)

        self.addPage(self._welcome)
        self.addPage(self._ffmpeg)
        self.addPage(self._model)
        self.addPage(self._dirs)

    def accept(self):
        self._apply()
        super().accept()

    def reject(self):
        from ...config import set_config, get_config
        set_config("setup_completed", True)
        super().reject()

    def _apply(self):
        from ...config import set_config, get_config_manager

        lang = self._welcome.selected_language()
        model = self._model.selected_model()
        cache = self._model.cache_dir()
        out_dir = self._dirs.output_dir()
        temp_dir = self._dirs.temp_dir()
        cleanup = self._dirs.cleanup()
        notif = self._dirs.notifications()

        set_config("idioma", lang)
        from ..i18n import setup as i18n_setup
        i18n_setup(lang)
        set_config("whisper.modelo", model)
        set_config("directorios.cache_modelos", cache)
        set_config("directorios.temporal", temp_dir)
        set_config("salida.directorio", out_dir)
        set_config("procesamiento.limpiar_cache_temporal", cleanup)
        set_config("gui.notificaciones_sistema", notif)
        set_config("setup_completed", True)

        cc = self._welcome.get_community_config()
        set_config("comunidad.habilitado", cc["habilitado"])
        set_config("comunidad.subir_automaticamente", cc["subir_automaticamente"])
        set_config("comunidad.normalizacion_habilitada", cc["normalizacion_habilitada"])
        set_config("comunidad.share_consent_given", cc["share_consent_given"])

        ok = get_config_manager()._save()
        if not ok:
            logger.error("Failed to persist setup wizard config!")
        elif not get_config_manager().get("setup_completed", False):
            logger.error("Save verification failed: setup_completed not persisted!")

        logger.info(
            "Setup wizard completed: lang=%s model=%s cache=%s",
            lang, model, cache,
        )
