"""Cleanup actions dialog — lets user choose what to clean."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QMessageBox, QVBoxLayout, QWidget,
)

from ...utils.system import clean_temp, clean_logs, clean_hf_cache
from ..i18n import _


class DiskCleanupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Limpiar"))
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        lbl = QLabel(_("Selecciona que deseas limpiar:"))
        layout.addWidget(lbl)

        self._temp_cb = QCheckBox(_("Archivos temporales"))
        self._temp_cb.setChecked(True)
        layout.addWidget(self._temp_cb)

        self._logs_cb = QCheckBox(_("Logs"))
        self._logs_cb.setChecked(True)
        layout.addWidget(self._logs_cb)

        self._hf_cb = QCheckBox(_("Cache de HuggingFace (descargas)"))
        self._hf_cb.setChecked(False)
        self._hf_cb.setStyleSheet("color: #c00;")
        layout.addWidget(self._hf_cb)

        layout.addSpacing(4)

        warn = QLabel(
            _("La cache de HuggingFace requiere descargar\nlos modelos nuevamente si se usan.")
        )
        warn.setStyleSheet("color: #888; font-size: 9pt;")
        warn.setWordWrap(True)
        layout.addWidget(warn)

        layout.addSpacing(8)

        self._reset_cb = QCheckBox(_("Restablecer configuracion (mostrar asistente al iniciar)"))
        self._reset_cb.setChecked(False)
        layout.addWidget(self._reset_cb)

        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(_("Limpiar"))
        buttons.accepted.connect(self._on_clean)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_clean(self):
        total = 0
        if self._temp_cb.isChecked():
            total += clean_temp()
        if self._logs_cb.isChecked():
            total += clean_logs()
        if self._hf_cb.isChecked():
            total += clean_hf_cache()

        msgs = []
        if total > 0:
            mb = total / (1024 * 1024)
            msgs.append(f"{_('Se liberaron')} {mb:.1f} MB {_('de espacio.')}")

        if self._reset_cb.isChecked():
            from ...config import set_config, get_config_manager
            set_config("setup_completed", False)
            get_config_manager()._save()
            msgs.append(
                _("Configuracion restablecida.\nEl asistente se mostrara al reiniciar la aplicacion.")
            )

        if msgs:
            QMessageBox.information(
                self, _("Limpieza completada"), "\n\n".join(msgs),
            )
        self.accept()
