"""Main window for MADRAC-SUBS v3."""

import logging
import queue as _queue
import re
import sys
import threading
import traceback
from pathlib import Path
from typing import Any, List, Optional

from PySide6.QtCore import Qt, QTimer, Slot, QUrl, QVariantAnimation, Signal
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QIcon, QDesktopServices, QColor
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QFrame, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QMainWindow, QMenu, QPlainTextEdit, QProgressBar, QPushButton,
    QSplitter, QStackedWidget, QSystemTrayIcon, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .. import __version__
from ..core import get_logger, get_bus
from ..core.paths import get_base_path
from ..config import get_config, set_config
from ..pipeline.queue import ProcessingState
from ..supabase_client import CLIENTE
from ..utils.media import (
    mux_subtitles, demux_subtitles, detect_subtitles,
    strip_subtitles, lang_639_2b, probe_media,
)
from ..utils.ffmpeg import pick_best_track, extract_subtitle_track, get_duration as _get_duration
from ..utils.hashing import sha256 as _sha256
from .dialogs import AboutDialog, ExtensionsDialog
from .dialogs.editor_dialog import EditorDialog
from .dub_dialog import DubDialog
from ..dubbing.manager import DubbingManager
from .i18n import _

logger = get_logger("ui.main_window")

_VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v", ".wmv"}
_SUBTITLE_EXTS = {".srt", ".vtt", ".ass"}

_STATE_LABELS = {
    ProcessingState.PENDING: _("Pendiente"),
    ProcessingState.PROCESSING: _("Procesando"),
    ProcessingState.COMPLETED: _("Completado"),
    ProcessingState.FAILED: _("Falló"),
    ProcessingState.CANCELLED: _("Cancelado"),
}


def _estimate_dubbing_time(srt_path: str, high_quality: bool) -> int:
    """Heuristic estimate of dubbing processing time in minutes.

    Reads the SRT to get approximate video duration from the last timestamp.
    Does NOT block (simple O(n) regex pass, <10ms for any SRT).
    """
    last_ms = 0
    try:
        with open(srt_path, "r", encoding="utf-8-sig") as _f:
            for _line in _f:
                _m = re.match(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", _line)
                if _m:
                    _h, _min, _s, _ms = (
                        int(_m.group(1)), int(_m.group(2)),
                        int(_m.group(3)), int(_m.group(4)),
                    )
                    _val = _h * 3600000 + _min * 60000 + _s * 1000 + _ms
                    if _val > last_ms:
                        last_ms = _val
    except Exception:
        pass

    duration_min = last_ms / 60000.0

    if high_quality:
        return max(5, int(duration_min * 15 + 2))
    return max(1, int(duration_min * 0.1 + 1))


class _LogHandler(logging.Handler):
    def __init__(self, queue):
        super().__init__()
        self._queue = queue
        self.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)-7s] %(message)s",
            datefmt="%H:%M:%S",
        ))

    def emit(self, record):
        msg = self.format(record)
        level = record.levelname
        color = "#888"
        if level == "ERROR" or level == "CRITICAL":
            color = "#f44"
        elif level == "WARNING":
            color = "#fa0"
        elif level == "INFO":
            color = "#8af"
        elif level == "DEBUG":
            color = "#888"
        elif msg.startswith("[OK]"):
            color = "#2f2"
        elif msg.startswith("[ERR]") or msg.startswith("[ERROR]"):
            color = "#f44"
        elif msg.startswith("[WARN]"):
            color = "#fa0"
        elif msg.startswith("[INFO]"):
            color = "#8af"
        html = f'<span style="color:{color}">{self._escape_html(msg)}</span>'
        self._queue.put(html)

    def _escape_html(self, text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class MainWindow(QMainWindow):
    """Main application window."""

    notification_requested = Signal(str)

    def __init__(
        self,
        worker: Any = None,
        queue_mgr: Any = None,
        config_mgr: Any = None,
        event_bus: Any = None,
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self._worker = worker
        self._queue_mgr = queue_mgr
        self._config_mgr = config_mgr
        self._bus = event_bus or get_bus()
        self._log_queue: _queue.Queue = _queue.Queue()

        self._setup_window()
        self._setup_central()
        self._setup_bottom_bar()
        self._setup_tray()
        self._connect_worker()
        self._subscribe_events()
        self._setup_log_capture()
        self._start_timers()
        self._restore_state()
        self._refresh_queue()
        if CLIENTE.is_logged_in():
            QTimer.singleShot(0, self._check_community_batch)

        logger.info("MainWindow ready")

    # Status bar animation (V2 style)
    def _aplicar_color_barra(self, color):
        self._status_bar.setStyleSheet(f"background-color: {color.name()}; border: none;")

    def _toggle_anim_barra(self):
        if self._barra_colapsada:
            d = self._anim_bar.direction()
            self._anim_bar.setDirection(
                QVariantAnimation.Backward if d == QVariantAnimation.Forward
                else QVariantAnimation.Forward
            )
            self._anim_bar.start()

    def _iniciar_anim_barra(self, light_hex: str, dark_hex: str):
        self._anim_bar.setStartValue(QColor(light_hex))
        self._anim_bar.setEndValue(QColor(dark_hex))
        self._anim_bar.setDirection(QVariantAnimation.Forward)
        self._anim_bar.start()

    def _detener_anim_barra(self, solid_hex: str = ""):
        self._anim_bar.stop()
        if solid_hex:
            self._status_bar.show()
            self._aplicar_color_barra(QColor(solid_hex))
        else:
            self._status_bar.hide()

    # Debounced status bar update (V2 style)
    def _actualizar_barra_estado(self):
        self._barra_colapsada = self._log_group.height() < 9

        if self._first_bar_check:
            self._first_bar_check = False
            saved = get_config('gui.splitter_sizes')
            was_collapsed = get_config('gui.log_collapsed', False)
            if saved and len(saved) == 2:
                if was_collapsed:
                    saved[1] = 8
                self._splitter.setSizes(saved)
            else:
                sizes = self._splitter.sizes()
                self._splitter.setSizes([sizes[0], 40])
                if was_collapsed:
                    self._log_group.setMinimumHeight(8)
                    self._status_bar.show()
                    self._bar_visible = True
                    self._barra_colapsada = True
                    self._log_group.setTitle("")
                    self._iniciar_anim_barra("#34c759", "#1e7e34")

        # Log title hides at < 25px
        h_log = self._log_group.height()
        if h_log < 25:
            self._log_group.setTitle("")
        elif not self._log_group.title():
            self._log_group.setTitle("Actividad")

        # Show/hide status bar
        if self._ultimo_log_error:
            self._detener_anim_barra("#dc3545")
            self._bar_visible = True
        elif self._barra_colapsada:
            if not self._bar_visible:
                self._status_bar.show()
                self._bar_visible = True
            if self._procesamiento_activo:
                self._iniciar_anim_barra("#ff9f0a", "#d35400")
            else:
                self._iniciar_anim_barra("#34c759", "#1e7e34")
        elif h_log > 20 and self._bar_visible:
            self._detener_anim_barra()
            self._bar_visible = False

    # ------------------------------------------------------------------ setup

    def _setup_window(self):
        self.setWindowTitle(f"MADRAC-SUBS {__version__}")
        self.setMinimumSize(640, 480)
        self.setMenuBar(None)
        icon_path = get_base_path() / "ui" / "madrac-subs.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        else:
            svg = get_base_path() / "ui" / "madrac-subs.svg"
            if svg.exists():
                self.setWindowIcon(QIcon(str(svg)))

    def _setup_top_bar(self):
        top = QWidget()
        top.setFixedHeight(40)
        row = QHBoxLayout(top)
        row.setContentsMargins(6, 2, 6, 2)
        row.setSpacing(4)

        btn_style = (
            "QPushButton {"
            "  min-height: 36px;"
            "  font-size: 11pt;"
            "  padding-left: 12px;"
            "  padding-right: 12px;"
            "  border: 1px solid #444;"
            "  border-radius: 4px;"
            "  background: #2d2d2d;"
            "  color: #eee;"
            "}"
            "QPushButton:hover { background: #3a3a3a; }"
            "QPushButton:pressed { background: #1e1e1e; }"
            "QPushButton:disabled { color: #666; background: #222; }"
        )

        self._add_btn = QPushButton(_("Examinar"))
        self._add_btn.setStyleSheet(btn_style)
        self._add_btn.clicked.connect(self._on_add_files)
        row.addWidget(self._add_btn)

        self._add_folder_btn = QPushButton(_("Agregar Carpeta"))
        self._add_folder_btn.setStyleSheet(btn_style)
        self._add_folder_btn.clicked.connect(self._on_add_folder)
        row.addWidget(self._add_folder_btn)

        self._ext_btn = QPushButton(_("Extensiones"))
        self._ext_btn.setStyleSheet(btn_style)
        self._ext_btn.clicked.connect(self._on_extensions)
        row.addWidget(self._ext_btn)

        row.addStretch()

        self._editor_btn = QPushButton(_("Editor"))
        self._editor_btn.setStyleSheet(btn_style)
        self._editor_btn.clicked.connect(self._on_editor)
        row.addWidget(self._editor_btn)

        self.btn_dub = QPushButton(_("Dub Now"))
        self.btn_dub.setObjectName("btn_dub")
        self.btn_dub.setToolTip(_("Doblar video con MADRAC-DUBS"))
        self.btn_dub.setStyleSheet(btn_style)
        self.btn_dub.setEnabled(False)
        self.btn_dub.clicked.connect(self._on_dub_now)
        row.addWidget(self.btn_dub)

        row.addStretch()

        if not get_config("file_handlers.registered", False):
            self._btn_integracion = QPushButton(_("Integrar en Windows"))
            self._btn_integracion.setStyleSheet("""
                QPushButton { background-color: #555; color: #aaa; font-weight: bold; padding: 4px 8px; border-radius: 4px; }
                QPushButton:hover { background-color: #27ae60; color: white; }
            """)
            self._btn_integracion.clicked.connect(self._registrar_integracion_windows)
            row.addWidget(self._btn_integracion)

        self._lbl_user = QLabel("")
        self._lbl_user.setStyleSheet("color: #aaa; font-size: 9pt; padding-right: 4px;")
        row.addWidget(self._lbl_user)

        self._btn_online = QPushButton(_("Online: OFF"))
        self._btn_online.setCheckable(True)
        self._btn_online.setFixedWidth(140)
        self._btn_online.setStyleSheet("""
            QPushButton { background-color: #555; color: #aaa; font-weight: bold; padding: 4px 8px; border-radius: 4px; }
            QPushButton:checked { background-color: #27ae60; color: white; }
        """)
        self._btn_online.toggled.connect(self._on_online_toggled)
        row.addWidget(self._btn_online)

        CLIENTE.loginFinished.connect(self._on_login_finished)
        # Restore last preference
        if get_config("comunidad.online", False) and not CLIENTE.is_logged_in():
            self._btn_online.setChecked(True)
        self._actualizar_estado_online()

        return top

    def _on_online_toggled(self, activo: bool):
        if activo:
            self._btn_online.setEnabled(False)
            self._btn_online.setText(_("Online: Conectando..."))
            CLIENTE.login_google_async()
        else:
            CLIENTE.logout()
            set_config("comunidad.online", False)
            self._actualizar_estado_online()

    def _on_login_finished(self, success: bool):
        self._btn_online.setEnabled(True)
        set_config("comunidad.online", success)
        self._actualizar_estado_online()
        if success:
            self._append_log(f"[OK] Sesion iniciada: {CLIENTE.get_nombre()}")
            self._check_community_batch()
        else:
            self._append_log("[WARN] Inicio de sesion cancelado o fallido")
            self._btn_online.blockSignals(True)
            self._btn_online.setChecked(False)
            self._btn_online.blockSignals(False)

    def _actualizar_estado_online(self):
        online = CLIENTE.is_logged_in()
        self._btn_online.blockSignals(True)
        self._btn_online.setChecked(online)
        self._btn_online.blockSignals(False)
        if online:
            self._btn_online.setText(f"Online: {CLIENTE.get_nombre()}")
            self._lbl_user.setText(CLIENTE.get_nombre())
        else:
            self._btn_online.setText("Online: OFF")
            self._lbl_user.setText("")

    def _registrar_integracion_windows(self) -> None:
        if sys.platform != "win32":
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, _("Integracion Windows"),
                _("Esta funcion solo esta disponible en Windows."))
            return
        try:
            from ..core.registry import registrar_drop_handler
            if registrar_drop_handler():
                if getattr(self, '_btn_integracion', None):
                    self._btn_integracion.hide()
                self._show_notification(_("Integracion Windows"),
                    _("Integrado! Click derecho > 'Muxear con Madrac-subs'..."))
                self._append_log("[OK] Integracion Windows completada")
            else:
                from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, _("Error"),
                _("No se pudo registrar la integracion en Windows.\nVerifica que tienes permisos de escritura en el registro."))
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, _("Error"),
                f"{_('No se pudo registrar la integracion')}:\n{e}")

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, _("Agregar carpeta"),
            get_config("gui.ultimo_directorio", ""),
        )
        if not folder:
            return
        set_config("gui.ultimo_directorio", folder)
        from pathlib import Path as _Path
        videos_found = 0
        for f in sorted(Path(folder).iterdir()):
            if f.suffix.lower() in {".mp4", ".mkv", ".avi", ".mov", ".webm", ".mp3", ".wav", ".flac", ".m4a"} and f.is_file():
                if self._queue_mgr:
                    entry = self._queue_mgr.add(str(f))
                    self._detect_subtitles_for_entry(entry)
                    videos_found += 1
        if videos_found:
            self._append_log(f"[OK] Added {videos_found} files from {Path(folder).name}")
            self._refresh_queue()
            if CLIENTE.is_logged_in():
                self._check_community_batch()
        else:
            self._append_log("[INFO] No media files found in selected folder")

    def _setup_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Top bar
        top_bar = self._setup_top_bar()
        layout.addWidget(top_bar)

        # 2-panel splitter: Queue | Log (V2 style)
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(8)
        splitter.setChildrenCollapsible(False)
        splitter.setStyleSheet("QSplitter::handle { background-color: #666; height: 8px; border: 1px solid #333; }")

        # Queue panel
        queue_group = QGroupBox(_("Cola de Procesamiento"))
        queue_group.setMinimumHeight(150)
        queue_group.setStyleSheet("QGroupBox { margin-top: 1.5ex; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 12px; padding: 0 3px; }")
        queue_layout = QVBoxLayout(queue_group)
        queue_layout.setContentsMargins(4, 12, 4, 4)

        self._table = QTreeWidget()
        self._table.setHeaderLabels([_("Archivo"), _("Estado"), _("Subt."), _("Com.")])
        self._table.setRootIsDecorated(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionMode(QTreeWidget.ExtendedSelection)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_table_context)
        self._table.itemDoubleClicked.connect(self._on_table_double_clicked)
        self._table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self._table.setIndentation(0)
        hdr = self._table.header()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setDefaultSectionSize(100)
        hdr.setMinimumSectionSize(80)
        self._table.setStyleSheet("QTreeWidget { border: 1px solid #333; } QHeaderView::section { background: #252525; color: #ccc; padding: 4px; border: none; border-right: 1px solid #333; font-weight: bold; }")
        queue_layout.addWidget(self._table)

        # Log panel (Actividad) — V2 style
        self._log_group = QGroupBox(_("Actividad"))
        self._log_group.setMinimumHeight(8)
        self._log_group.setStyleSheet("QGroupBox { margin-top: 1.5ex; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 12px; padding: 0 3px; }")
        log_layout = QVBoxLayout(self._log_group)
        log_layout.setContentsMargins(4, 12, 4, 4)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(1000)
        self._log_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._log_view.setStyleSheet("QPlainTextEdit { background: #1a1a1a; color: #ccc; border: 1px solid #333; font-family: 'Consolas', 'Monospace'; font-size: 9pt; }")
        log_layout.addWidget(self._log_view)

        splitter.addWidget(queue_group)
        splitter.addWidget(self._log_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)
        self._splitter = splitter

        # Status bar at bottom (V2 style — shows when log collapsed)
        self._status_bar = QFrame()
        self._status_bar.setFixedHeight(13)
        self._status_bar.setStyleSheet("background-color: #2ecc71; border: none;")
        self._status_bar.hide()
        layout.addWidget(self._status_bar)

        # Splitter move handler (debounced)
        self._debounce_bar = QTimer(self)
        self._debounce_bar.setSingleShot(True)
        self._debounce_bar.timeout.connect(self._actualizar_barra_estado)
        self._splitter.splitterMoved.connect(lambda: self._debounce_bar.start(80))

        # Animation for status bar
        self._anim_bar = QVariantAnimation()
        self._anim_bar.setDuration(1500)
        self._anim_bar.setLoopCount(-1)
        self._anim_bar.valueChanged.connect(self._aplicar_color_barra)
        self._anim_bar.finished.connect(self._toggle_anim_barra)

        # State
        self._barra_colapsada = False
        self._bar_visible = False
        self._ultimo_log_error = False
        self._first_bar_check = True
        self._procesamiento_activo = False

    def _setup_bottom_bar(self):
        bottom = QWidget()
        bottom.setFixedHeight(72)
        bar = QVBoxLayout(bottom)
        bar.setContentsMargins(6, 2, 6, 4)
        bar.setSpacing(3)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        btn_style = (
            "QPushButton {"
            "  min-height: 36px;"
            "  font-size: 11pt;"
            "  padding-left: 16px;"
            "  padding-right: 16px;"
            "  border: 1px solid #444;"
            "  border-radius: 4px;"
            "  background: #2d2d2d;"
            "  color: #eee;"
            "}"
            "QPushButton:hover { background: #3a3a3a; }"
            "QPushButton:pressed { background: #1e1e1e; }"
            "QPushButton:disabled { color: #666; background: #222; }"
        )

        self._start_btn = QPushButton("\u25B6 " + _("Iniciar Transcripcion"))
        self._start_btn.setStyleSheet(btn_style)
        self._start_btn.clicked.connect(self._on_start)
        self._start_btn.setEnabled(False)
        btn_row.addWidget(self._start_btn)

        self._cancel_btn = QPushButton("\u23F9 " + _("Cancelar Todo"))
        self._cancel_btn.setStyleSheet(btn_style)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._cancel_btn.setEnabled(False)
        btn_row.addWidget(self._cancel_btn)

        self._open_results_btn = QPushButton("\U0001F4C2 " + _("Abrir Carpeta Resultados"))
        self._open_results_btn.setStyleSheet(btn_style)
        self._open_results_btn.clicked.connect(self._on_open_results)
        btn_row.addWidget(self._open_results_btn)

        btn_row.addStretch()
        bar.addLayout(btn_row)

        self._add_bottom_bar(bottom)

    def _add_bottom_bar(self, widget):
        cl = self.centralWidget().layout()
        if cl:
            cl.addWidget(widget)

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self.windowIcon(), self)
        tm = QMenu()
        a = tm.addAction(_("Show/Hide"))
        a.triggered.connect(self._toggle_visible)
        tm.addSeparator()
        a = tm.addAction(_("Quit"))
        a.triggered.connect(self.close)
        self._tray.setContextMenu(tm)
        self._tray.activated.connect(self._on_tray_activated)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray.show()

    # --------------------------------------------------------------- signals

    def _connect_worker(self):
        if not self._worker:
            return
        w = self._worker
        w.started.connect(self._on_worker_started)
        w.progress.connect(self._on_worker_progress)
        w.log.connect(self._append_log)
        w.finished.connect(self._on_worker_finished)
        w.all_completed.connect(self._on_all_completed)

    def _subscribe_events(self):
        self._bus.subscribe("queue.added", lambda d: QTimer.singleShot(0, self._refresh_queue))
        self._bus.subscribe("queue.removed", lambda d: QTimer.singleShot(0, self._refresh_queue))
        self._bus.subscribe("queue.state_changed", lambda d: QTimer.singleShot(0, self._refresh_queue))
        self._bus.subscribe("worker.state", self._on_worker_state_event)

    def _setup_log_capture(self):
        logging.getLogger("madrac").addHandler(_LogHandler(self._log_queue))

    def _start_timers(self):
        self._log_timer = QTimer(self)
        self._log_timer.timeout.connect(self._flush_log_queue)
        self._log_timer.start(150)

    # ------------------------------------------------------------------ slots

    def _on_add_files(self):
        files, _filt = QFileDialog.getOpenFileNames(
            self, _("Select media files"),
            get_config("gui.ultimo_directorio", ""),
            _("Media files (*.mp4 *.mkv *.avi *.mov *.webm *.mp3 *.wav *.flac *.m4a *.aac);;All files (*.*)"),
        )
        if not files:
            return
        set_config("gui.ultimo_directorio", str(Path(files[0]).parent))
        if self._queue_mgr:
            for f in files:
                entry = self._queue_mgr.add(f)
                self._detect_subtitles_for_entry(entry)
        self._refresh_queue()
        if CLIENTE.is_logged_in():
            self._check_community_batch()

    def _on_start(self):
        if not self._worker or not self._queue_mgr:
            return
        if not self._worker.isRunning():
            self._worker.start()
            self._append_log("[INFO] Worker started")

    def _on_cancel(self):
        if self._worker:
            self._worker.cancel()
            self._append_log("[INFO] Cancel requested")

    def _on_clear(self):
        if self._queue_mgr:
            removed = self._queue_mgr.clear_all()
            if removed:
                self._append_log(f"[INFO] Cleared {removed} items")
            self._refresh_queue()

    def _on_extensions(self):
        dlg = ExtensionsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.notification_requested.emit(_("Ajustes guardados"))

    def _on_editor(self):
        path = self._selected_subtitle_path()
        video_hash = ""
        video_duration_s = 0.0
        entry_path = ""
        share_candidate = False
        if path:
            entry = self._queue_entry_for_selected()
            if entry:
                video_hash = entry.metadata.get("video_hash", "")
                video_duration_s = entry.metadata.get("duration_s", 0.0)
                entry_path = entry.ruta
                share_candidate = entry.metadata.get("share_candidate", False)
        if not path:
            path, _filt = QFileDialog.getOpenFileName(
                self, _("Abrir subtitulos"), "",
                _("Subtitulos (*.srt *.vtt *.ass);;Todos (*.*)"),
            )
        dlg = EditorDialog(path or "", self,
                           video_hash=video_hash,
                           video_duration_s=video_duration_s,
                           entry_path=entry_path,
                           share_candidate=share_candidate)
        dlg.exec()

    def _selected_subtitle_path(self) -> Optional[str]:
        items = self._table.selectedItems()
        if not items:
            return None
        return self._subtitle_path_for_item(items[0])

    def _queue_entry_for_selected(self) -> Optional[Any]:
        items = self._table.selectedItems()
        if not items or not self._queue_mgr:
            return None
        return self._queue_mgr.get(items[0].data(0, Qt.UserRole))

    def _subtitle_path_for_item(self, item) -> Optional[str]:
        if not self._queue_mgr:
            return None
        entry_id = item.data(0, Qt.UserRole)
        entry = self._queue_mgr.get(entry_id)
        if not entry:
            return None
        # 1. Pipeline output (completed items)
        if entry.state == ProcessingState.COMPLETED:
            p = entry.output_path
            if p and Path(p).suffix.lower() in _SUBTITLE_EXTS and Path(p).exists():
                return p
        # 2. Subtitle file next to video (same stem)
        vid = Path(entry.ruta)
        for ext in _SUBTITLE_EXTS:
            candidate = vid.with_suffix(ext)
            if candidate.exists():
                return str(candidate)
        return None

    def _open_subeditor(self, path: str, entry: Any = None) -> None:
        video_hash = entry.metadata.get("video_hash", "") if entry else ""
        video_duration_s = entry.metadata.get("duration_s", 0.0) if entry else 0.0
        entry_path = entry.ruta if entry else ""
        share_candidate = entry.metadata.get("share_candidate", False) if entry else False
        dlg = EditorDialog(path, self,
                           video_hash=video_hash,
                           video_duration_s=video_duration_s,
                           entry_path=entry_path,
                           share_candidate=share_candidate)
        dlg.exec()

    def _on_table_double_clicked(self, item, column) -> None:
        path = self._subtitle_path_for_item(item)
        if path:
            entry = self._queue_mgr.get(item.data(0, Qt.UserRole)) if self._queue_mgr else None
            self._open_subeditor(path, entry)

    def _on_about(self):
        AboutDialog(self).exec()

    # ------------------------------------------------------------ Dub Now

    def _on_dub_now(self):
        items = self._table.selectedItems()
        if not items or not self._queue_mgr:
            return
        entry = self._queue_mgr.get(items[0].data(0, Qt.UserRole))
        if not entry:
            return

        video_path = Path(entry.ruta)
        if video_path.suffix.lower() not in _VIDEO_EXTS:
            from PySide6.QtWidgets import QMessageBox as _QMB
            _QMB.warning(self, _("Dub Now"),
                         _("El elemento seleccionado no es un video."))
            return

        if self._worker and self._worker.isRunning():
            from PySide6.QtWidgets import QMessageBox as _QMB
            _QMB.warning(self, _("Dub Now"),
                         _("Esperá a que termine la transcripción antes de doblar."))
            return

        srt_path = self._subtitle_path_for_item(items[0])
        if not srt_path:
            from PySide6.QtWidgets import QMessageBox as _QMB
            _QMB.warning(self, _("Dub Now"),
                         _("No se encontraron subtitulos para este video.\n"
                           "Transcriba el video primero."))
            return

        dlg = DubDialog(video_path.name, self)
        dlg.config_confirmed.connect(lambda cfg: self._start_dubbing(
            str(video_path), srt_path, cfg, dlg
        ))
        dlg.cancelled.connect(dlg.reject)
        dlg.exec()

    def _start_dubbing(self, video_path: str, srt_path: str, config: dict, dlg: DubDialog):
        dubs_python = get_config("dubbing.dubs_python_path", "")
        if not dubs_python:
            from PySide6.QtWidgets import QMessageBox as _QMB
            _QMB.warning(self, _("Dub Now"),
                         _("La ruta a MADRAC-DUBS no esta configurada.\n"
                           "Configure 'dubbing.dubs_python_path' en la configuracion."))
            dlg.reject()
            return

        video_dir = Path(video_path).parent
        video_stem = Path(video_path).stem
        output_path = str(video_dir / f"{video_stem}_dubbed.mkv")

        manager = DubbingManager(dubs_python)
        manager.health_check_failed.connect(
            lambda err: self._dub_on_health_failed(err, dlg)
        )
        manager.job_progress.connect(lambda p, s, m: dlg.set_progress(p, s, m))
        manager.job_completed.connect(
            lambda out: self._dub_on_completed(out, manager, dlg)
        )
        manager.job_failed.connect(
            lambda err: self._dub_on_job_failed(err, manager, dlg)
        )

        self._append_log(f"[DUB] Starting: {video_path} -> {output_path}")

        estimated_min = _estimate_dubbing_time(srt_path, config.get("high_quality", False))
        if config.get("high_quality", False):
            estimate_msg = (
                "Alta calidad activada.\n"
                "Procesando con Demucs.\n\n"
                f"Tiempo estimado: ~{estimated_min} min\n"
                "(Esta estimación puede variar según el hardware.)"
            )
        else:
            estimate_msg = (
                "Modo rápido (DSP).\n"
                f"Tiempo estimado: ~{estimated_min} min"
            )
        dlg.set_progress(0, "estimating", estimate_msg)
        self._append_log(f"[DUB] Estimación: ~{estimated_min} min")

        import threading as _t
        _t.Thread(target=self._dub_worker, args=(
            manager, video_path, srt_path, output_path, config
        ), daemon=True).start()

    def _dub_worker(self, manager: DubbingManager, video_path: str,
                    srt_path: str, output_path: str, config: dict):
        if not manager.launch_dubs():
            return

        try:
            job_id = manager.submit_job(video_path, srt_path, output_path, config)
            if not job_id:
                logger.error("[DUB] submit_job returned None — check manager logs")
                manager.shutdown()
                return
        except Exception as e:
            logger.error("[DUB] submit_job exception: %s", e)
            logger.error(traceback.format_exc())
            manager.shutdown()
            return

        import time as _time
        self._dub_cancelled = False
        while not self._dub_cancelled:
            _time.sleep(2)
            try:
                data = manager.poll_job(job_id)
            except OSError as e:
                if e.errno == 22:
                    logger.error("[DUB] Poll OSError 22 — DUBS may have crashed")
                    _time.sleep(2)
                    try:
                        data = manager.poll_job(job_id)
                    except Exception as e2:
                        logger.error("[DUB] Poll failed after retry: %s", e2)
                        logger.error(traceback.format_exc())
                        manager.shutdown()
                        return
                else:
                    logger.error("[DUB] Poll OSError %d: %s", e.errno, e)
                    manager.shutdown()
                    return
                continue
            except Exception as e:
                logger.error("[DUB] Poll exception: %s", e)
                logger.error(traceback.format_exc())
                manager.shutdown()
                return

            status = data.get("status", "")
            if status in ("completed", "failed"):
                manager.shutdown()
                break
        manager.shutdown()

    def _dub_on_health_failed(self, error: str, dlg: DubDialog):
        dlg.set_error(error)
        self._append_log(f"[DUB] Health check failed: {error}")

    def _dub_on_completed(self, output_path: str, manager: DubbingManager, dlg: DubDialog):
        dlg.set_completed()
        self._append_log(f"[DUB] Completed: {output_path}")
        QTimer.singleShot(1000, lambda: self._open_dubbed_result(output_path, dlg))

    def _dub_on_job_failed(self, error: str, manager: DubbingManager, dlg: DubDialog):
        self._dub_cancelled = True
        logger.error(f"[DUB] Failed: {type(error).__name__}: {error}")
        logger.error(traceback.format_exc())
        if dlg:
            dlg.set_error(error)

    def _open_dubbed_result(self, output_path: str, dlg: DubDialog):
        dlg.accept()
        output = Path(output_path)
        if output.exists():
            self._append_log(f"[DUB] Output: {output_path}")
            import subprocess as _sp
            _sp.Popen(["explorer", "/select,", str(output)])

    def _toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._toggle_visible()

    # --------------------------------------------------------- worker signals

    @Slot(str)
    def _on_worker_started(self, item_id):
        self._procesamiento_activo = True
        self._update_buttons()
        self._actualizar_barra_estado()

    @Slot(str, float, str)
    def _on_worker_progress(self, item_id, pct, stage):
        self._update_item_row(item_id, pct, stage)

    @Slot(str)
    def _append_log(self, msg):
        if msg.startswith("[OK]"):
            color = "#2f2"
        elif msg.startswith("[ERR]") or msg.startswith("[ERROR]"):
            color = "#f44"
            self._ultimo_log_error = True
        elif msg.startswith("[WARN]"):
            color = "#fa0"
        elif msg.startswith("[INFO]"):
            color = "#8af"
        else:
            color = "#ccc"
        html = f'<span style="color:{color}">{self._escape_html(msg)}</span>'
        self._log_view.appendHtml(html)
        self._actualizar_barra_estado()

    def _escape_html(self, text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @Slot(str, bool, str)
    def _on_worker_finished(self, item_id, success, error):
        self._refresh_queue()
        self._update_buttons()
        title = _("Completado") if success else _("Falló")
        msg = _("Item processed successfully") if success else (error or _("Falló"))
        self._show_notification(title, msg)
        if success and CLIENTE.is_logged_in():
            self._check_community_batch()

    @Slot()
    def _on_all_completed(self):
        self._procesamiento_activo = False
        self._update_buttons()
        self._actualizar_barra_estado()
        self._show_notification(_("Completado"), _("Todos los elementos de la cola han sido procesados"))
        self._update_buttons()
        self._show_notification(_("Completado"), _("Todos los elementos de la cola han sido procesados"))

    # ------------------------------------------------------------ event bus

    def _on_worker_state_event(self, data):
        state = data.get("state", "")
        # No progress bar in V2 style; status bar handles progress

    # --------------------------------------------------------------- log flus

    def _flush_log_queue(self):
        while not self._log_queue.empty():
            try:
                html = self._log_queue.get_nowait()
                self._log_view.appendHtml(html)
            except _queue.Empty:
                break

    # ---------------------------------------------------------------- table

    def _refresh_queue(self):
        if not self._queue_mgr:
            return
        items = self._queue_mgr.list_all()
        self._table.clear()
        for entry in items:
            self._insert_item(entry)
        self._update_buttons()

    def _insert_item(self, entry):
        name = Path(entry.ruta).name
        status = _STATE_LABELS.get(entry.state, entry.state.name)

        sub_info = self._format_subtitle_info(entry)
        item = QTreeWidgetItem([name, status, sub_info, ""])
        item.setData(0, Qt.UserRole, entry.id)
        item.setToolTip(0, entry.ruta)

        if entry.state == ProcessingState.COMPLETED:
            item.setForeground(1, Qt.darkGreen)
        elif entry.state == ProcessingState.FAILED:
            item.setForeground(1, Qt.red)
        elif entry.state == ProcessingState.PROCESSING:
            item.setForeground(1, Qt.blue)
        elif entry.state == ProcessingState.CANCELLED:
            item.setForeground(1, Qt.gray)

        disponible = entry.metadata.get("community_available", None)
        if disponible is True:
            item.setText(3, "☑")
            item.setForeground(3, QColor("#2ecc40"))
        else:
            item.setText(3, "☐")
            item.setForeground(3, QColor("#555"))
        item.setTextAlignment(3, Qt.AlignCenter)

        self._table.addTopLevelItem(item)

    @staticmethod
    def _format_subtitle_info(entry) -> str:
        meta = entry.metadata or {}
        sub_info = meta.get("sub_info", {})
        parts = []
        if sub_info.get("companion"):
            parts.append("C")
        if sub_info.get("embedded"):
            langs = sub_info["embedded"].get("languages", [])
            if langs:
                lang_str = ",".join(langs[:3])
                if len(langs) > 3:
                    lang_str += "..."
                parts.append(f"E:{lang_str}")
            else:
                parts.append("E")
        return " ".join(parts) if parts else ""

    def _check_community_batch(self):
        if not CLIENTE.is_logged_in() or not self._queue_mgr:
            return
        entries = self._queue_mgr.list_all()
        if not entries:
            return
        self._append_log("[INFO] Revisando disponibilidad en comunidad...")

        def _work():
            for entry in list(entries):
                try:
                    video_hash = _sha256(Path(entry.ruta))
                    if not video_hash:
                        continue
                    duration = _get_duration(entry.ruta)
                    matches = CLIENTE.buscar_por_hash(
                        video_hash, idioma="es",
                        duracion_seg=duration, tolerancia_seg=3.0,
                    )
                    available = len(matches) > 0
                    self._queue_mgr.update(entry.id, metadata={
                        **entry.metadata,
                        "community_available": available,
                        "video_hash": video_hash,
                    })
                except Exception:
                    self._queue_mgr.update(entry.id, metadata={
                        **entry.metadata,
                        "community_available": False,
                    })
            QTimer.singleShot(0, self._refresh_queue)

        threading.Thread(target=_work, daemon=True).start()

    def _detect_subtitles_for_entry(self, entry):
        info = {}
        vid = Path(entry.ruta)
        ext = vid.suffix.lower()
        if ext not in _VIDEO_EXTS:
            return
        probe = probe_media(entry.ruta)
        if probe.get("subtitle_streams", 0) > 0:
            info["embedded"] = {
                "streams": probe["subtitle_streams"],
                "languages": probe.get("subtitle_languages", []),
            }
        companions = []
        for sext in _SUBTITLE_EXTS:
            candidate = vid.with_suffix(sext)
            if candidate.exists():
                companions.append(str(candidate))
        if companions:
            info["companion"] = companions
        if info:
            self._queue_mgr.update(entry.id, metadata={**entry.metadata, "sub_info": info})

    def _update_item_row(self, item_id, pct, stage):
        for i in range(self._table.topLevelItemCount()):
            item = self._table.topLevelItem(i)
            if item and item.data(0, Qt.UserRole) == item_id:
                item.setText(1, f"Procesando {pct:.0f}%")
                item.setForeground(1, Qt.blue)
                break

    def _update_buttons(self):
        if not self._queue_mgr or not self._worker:
            self._start_btn.setEnabled(False)
            self._cancel_btn.setEnabled(False)
            return
        has_pending = self._queue_mgr.has_pending()
        is_running = self._worker.isRunning()
        self._start_btn.setEnabled(has_pending and not is_running)
        self._cancel_btn.setEnabled(is_running)

    # ---------------------------------------------------------- selection

    def _on_table_selection_changed(self):
        items = self._table.selectedItems()
        if not items or not self._queue_mgr:
            self.btn_dub.setEnabled(False)
            return
        item = items[0]
        entry_id = item.data(0, Qt.UserRole)
        entry = self._queue_mgr.get(entry_id)
        if not entry:
            self.btn_dub.setEnabled(False)
            return
        vid = Path(entry.ruta)
        is_video = vid.suffix.lower() in _VIDEO_EXTS
        has_srt = bool(self._subtitle_path_for_item(item))
        self.btn_dub.setEnabled(is_video and has_srt)

    # ---------------------------------------------------------- context menu

    def _on_table_context(self, pos):
        item = self._table.itemAt(pos)
        if not item or not self._queue_mgr:
            menu = QMenu()
            a = menu.addAction(_("Limpiar lista"))
            a.setEnabled(bool(self._queue_mgr and self._queue_mgr.count()))
            a.triggered.connect(self._on_clear)
            if not menu.isEmpty():
                menu.exec(self._table.viewport().mapToGlobal(pos))
            return
        entry_id = item.data(0, Qt.UserRole)
        entry = self._queue_mgr.get(entry_id)
        if not entry:
            return

        menu = QMenu()

        # Retry — only for failed/cancelled
        a = menu.addAction(_("Reintentar"))
        a.setEnabled(entry.state in (ProcessingState.FAILED, ProcessingState.CANCELLED))
        a.triggered.connect(lambda _, e=entry_id: self._retry_item(e))

        # Cancel — only for pending/processing
        a = menu.addAction(_("Cancelar"))
        a.setEnabled(entry.state in (ProcessingState.PENDING, ProcessingState.PROCESSING))
        a.triggered.connect(lambda _, e=entry_id: self._cancel_item(e))

        # Remove — always available
        a = menu.addAction(_("Eliminar de la cola"))
        a.triggered.connect(lambda _, e=entry_id: self._remove_item(e))

        menu.addSeparator()

        # Edit subtitles — available if subtitle file found (pipeline output or next to video)
        sub_path = self._subtitle_path_for_item(item)
        a = menu.addAction(_("Editar subtitulos"))
        a.setEnabled(bool(sub_path))
        if sub_path:
            a.triggered.connect(lambda _, p=sub_path: self._open_subeditor(p))

        # Mux — completed + video exists + subtitle exists
        can_mux = entry.state == ProcessingState.COMPLETED
        vid = Path(entry.ruta)
        srt_path = entry.output_path
        if can_mux and vid.exists() and vid.suffix.lower() in _VIDEO_EXTS:
            if not srt_path or Path(srt_path).suffix.lower() not in _SUBTITLE_EXTS:
                srt_path = self._subtitle_path_for_item(item)
            has_srt = srt_path is not None and Path(srt_path).exists()
        else:
            has_srt = False
        a = menu.addAction(_("Muxear subtitulos en el video"))
        a.setEnabled(can_mux and has_srt)
        a.triggered.connect(lambda _, e=entry_id: self._mux_item(e))

        # Demux — video exists + embedded tracks (any state)
        tracks = []
        if vid.exists():
            tracks = detect_subtitles(entry.ruta)
        a = menu.addAction(_("Demuxear (extraer) subtitulos"))
        a.setEnabled(bool(tracks))
        a.triggered.connect(lambda _, e=entry_id: self._demux_item(e))

        # Open output folder
        can_open = entry.state == ProcessingState.COMPLETED and entry.output_path and Path(entry.output_path).exists()
        a = menu.addAction(_("Abrir carpeta de salida"))
        a.setEnabled(can_open)
        a.triggered.connect(lambda _, e=entry_id: self._open_output(e))

        menu.addSeparator()
        a = menu.addAction(_("Limpiar lista"))
        a.setEnabled(bool(self._queue_mgr.count()))
        a.triggered.connect(self._on_clear)

        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _retry_item(self, entry_id):
        if not self._queue_mgr:
            return
        self._queue_mgr.update(entry_id, error="", progress=0.0, stage="")
        self._queue_mgr.set_state(entry_id, ProcessingState.PENDING)
        self._refresh_queue()

    def _cancel_item(self, entry_id):
        if self._queue_mgr:
            self._queue_mgr.cancel(entry_id)

    def _remove_item(self, entry_id):
        if self._queue_mgr:
            self._queue_mgr.remove(entry_id)
            self._refresh_queue()

    def _open_output(self, entry_id):
        entry = self._queue_mgr.get(entry_id) if self._queue_mgr else None
        if entry and entry.output_path:
            p = Path(entry.output_path)
            if p.exists():
                import subprocess
                subprocess.Popen(["explorer", "/select,", str(p)])

    def _on_open_results(self):
        if not self._queue_mgr:
            return
        items = self._queue_mgr.list_all()
        target = None
        for entry in items:
            if entry.state == ProcessingState.COMPLETED and entry.output_path:
                target = Path(entry.output_path).parent
                break
        if not target and items:
            target = Path(items[0].ruta).parent
        if target and target.exists():
            import subprocess
            subprocess.Popen(["explorer", str(target)])

    def _mux_item(self, entry_id):
        entry = self._queue_mgr.get(entry_id) if self._queue_mgr else None
        if not entry:
            return
        video = Path(entry.ruta)
        srt = entry.output_path
        if not srt or Path(srt).suffix.lower() not in _SUBTITLE_EXTS:
            for item_idx in range(self._table.topLevelItemCount()):
                item = self._table.topLevelItem(item_idx)
                if item and item.data(0, Qt.UserRole) == entry_id:
                    srt = self._subtitle_path_for_item(item)
                    break
            if not srt:
                srt = str(video.with_suffix(".srt"))
        if not srt or not Path(srt).exists():
            self._append_log(f"[ERR] SRT not found for mux: {srt}")
            return
        idioma = lang_639_2b(get_config("traduccion.idioma_destino", "es"))
        try:
            muxed = mux_subtitles(str(video), srt, language=idioma)
            self._append_log(f"[OK] Muxed: {Path(muxed).name}")
            self._show_notification("Mux complete", f"Saved: {Path(muxed).name}")
        except Exception as e:
            self._append_log(f"[ERR] Mux failed: {e}")
            logger.warning("Mux error: %s", e)

    def _demux_item(self, entry_id):
        entry = self._queue_mgr.get(entry_id) if self._queue_mgr else None
        if not entry:
            logger.warning("Demux: entry %s not found", entry_id)
            return
        try:
            from ..utils.media import _ISO_639_2B_TO_NAME, _ISO_639_1_TO_2B
            tracks = detect_subtitles(entry.ruta)
            if not tracks:
                self._append_log("[WARN] No subtitle tracks found in this video")
                return
            best = pick_best_track(tracks)
            if not best:
                self._append_log("[WARN] No usable subtitle track found")
                return
            lang_code = best.get("language", "und")
            lang_name = _ISO_639_2B_TO_NAME.get(
                _ISO_639_1_TO_2B.get(lang_code, lang_code),
                lang_code,
            )
            srt_out = str(Path(entry.ruta).with_suffix(".srt"))
            if extract_subtitle_track(entry.ruta, best["index"], srt_out):
                self._append_log(f"[OK] Demuxed: {lang_name}")
                self._show_notification("Demux complete", f"Extracted: {lang_name}")
            else:
                self._append_log("[ERR] Failed to extract subtitle track — check FFmpeg logs")
        except Exception as e:
            self._append_log(f"[ERR] Demux failed: {e}")
            logger.warning("Demux error: %s", e)

    # ---------------------------------------------------------- notifications

    def _show_notification(self, title, message):
        if not get_config("gui.notificaciones_sistema", True):
            return
        if self._tray and QSystemTrayIcon.supportsMessages():
            self._tray.showMessage(title, message, QSystemTrayIcon.Information, 3000)

    # ------------------------------------------------------------- persist

    def _restore_state(self):
        w = get_config("gui.ventana_ancho", 1000)
        h = get_config("gui.ventana_alto", 800)
        x = get_config("gui.ventana_x", None)
        y = get_config("gui.ventana_y", None)
        self.resize(w, h)
        if x is not None and y is not None:
            self.move(x, y)
        sizes = get_config("gui.splitter_sizes", None)
        if sizes and isinstance(sizes, list) and len(sizes) == 2:
            try:
                self._splitter.setSizes(sizes)
            except Exception:
                pass

    def _save_state(self):
        set_config("gui.ventana_ancho", self.width())
        set_config("gui.ventana_alto", self.height())
        set_config("gui.ventana_x", self.x())
        set_config("gui.ventana_y", self.y())
        set_config("gui.splitter_sizes", self._splitter.sizes())

    def closeEvent(self, event):
        self._save_state()
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(2000)
        if self._queue_mgr:
            self._queue_mgr.close()
        self._tray.hide()
        event.accept()

    # ------------------------------------------------------------ drag & drop

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        from PySide6.QtWidgets import QMessageBox
        videos, srts = [], []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if not path or not Path(path).is_file():
                continue
            ext = Path(path).suffix.lower()
            if ext in _SUBTITLE_EXTS:
                srts.append(path)
            elif ext in _VIDEO_EXTS:
                videos.append(path)
        if videos and srts:
            msg = QMessageBox(self)
            msg.setWindowTitle(_("Files detected"))
            msg.setText(f"{len(videos)} video(s) + {len(srts)} sub(s)")
            btn_mux = msg.addButton(_("Mux pairs"), QMessageBox.ActionRole)
            btn_queue = msg.addButton(_("Queue only"), QMessageBox.ActionRole)
            btn_cancel = msg.addButton(_("Cancelar"), QMessageBox.RejectRole)
            msg.exec()
            clicked = msg.clickedButton()
            if clicked == btn_mux:
                self._mux_dropped(videos, srts)
                return
            if clicked == btn_queue:
                for v in videos:
                    if self._queue_mgr:
                        entry = self._queue_mgr.add(v)
                        self._detect_subtitles_for_entry(entry)
                self._refresh_queue()
                if CLIENTE.is_logged_in():
                    self._check_community_batch()
                return
            return
        accepted = 0
        for v in videos:
            if self._queue_mgr:
                entry = self._queue_mgr.add(v)
                self._detect_subtitles_for_entry(entry)
                accepted += 1
        if accepted:
            self._refresh_queue()
            if CLIENTE.is_logged_in():
                self._check_community_batch()
        event.acceptProposedAction()

    def _mux_dropped(self, videos, srts):
        srt_map = {Path(s).stem: s for s in srts}
        idioma = lang_639_2b(get_config("traduccion.idioma_destino", "es"))
        ok, fail = 0, 0
        for v in videos:
            base = Path(v).stem
            srt = srt_map.get(base)
            if not srt:
                continue
            try:
                mux_subtitles(v, srt, language=idioma)
                ok += 1
            except Exception as e:
                logger.warning("Drop mux failed for %s: %s", v, e)
                fail += 1
        if ok:
            self._append_log(f"[OK] Muxed: {ok} file(s)")
        if fail:
            self._append_log(f"[WARN] Mux failed: {fail} file(s)")
