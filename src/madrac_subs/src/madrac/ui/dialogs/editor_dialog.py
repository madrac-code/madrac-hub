"""Editor dialog — Easy Mode (video + navigation) and Expert Mode (table + preview)."""

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QSequentialAnimationGroup, QPauseAnimation, QEvent
from PySide6.QtGui import QKeySequence, QShortcut, QCloseEvent, QKeyEvent, QCursor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QHeaderView,
    QTableView, QPushButton, QFileDialog, QMessageBox,
    QWidget, QSplitter, QTextBrowser, QCheckBox,
    QStackedWidget, QLabel, QGraphicsOpacityEffect,
    QAbstractItemView,
)

from ...config import get_config, set_config
from ...supabase_client import CLIENTE
from ...utils.editor_model import SubtitleDocument, HistoryStack, SubtitleEntry
from ...utils.editor_operations import insert_entry
from ...utils.editor_io import load_srt, save_srt, load_vtt, save_vtt, save_ass, load_ass, detect_format
from ...utils import sha256 as compute_sha256
from ...utils.ffmpeg import get_duration as _get_duration
from ...core.parser import parse_video_filename
from ..models.subtitle_table_model import SubtitleTableModel
from .search_dialog import SearchDialog
from ..widgets.video_player_widget import VideoPlayerWidget
from ..widgets.subtitle_navigation import SubtitleNavigationWidget
from ..i18n import _


_SAVERS = {
    "srt": save_srt,
    "vtt": save_vtt,
    "ass": save_ass,
}

_LOADERS = {
    "srt": load_srt,
    "vtt": load_vtt,
    "ass": load_ass,
}

_VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".wmv"}


def _ms_to_str(ms: int) -> str:
    total = ms // 1000
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    r = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{r:03d}"


def _find_video_for_subtitle(subtitle_path: str) -> str:
    path = Path(subtitle_path)
    parent = path.parent
    stem = path.stem
    for ext in _VIDEO_EXTS:
        candidate = parent / f"{stem}{ext}"
        if candidate.exists():
            return str(candidate)
    return ""


class EditorDialog(QDialog):
    """Open, edit, save subtitle documents with undo/redo.
    Easy Mode: video player + navigation list.
    Expert Mode: table + text preview.
    """

    def __init__(self, path: str = "", parent: QWidget = None,
                 video_hash: str = "", video_duration_s: float = 0.0,
                 entry_path: str = "", share_candidate: bool = False):
        super().__init__(parent)
        self.setWindowTitle(_("Editor de subtitulos"))
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.resize(1024, 700)

        self._doc = SubtitleDocument()
        self._history = HistoryStack()
        self._subtitle_path = path
        self._video_path = ""
        self._video_hash = video_hash
        self._video_duration_s = video_duration_s
        self._entry_path = entry_path
        self._share_candidate = share_candidate
        self._expert_mode = get_config("editor.expert_mode", False)
        self._fullscreen_cooldown = False

        self._fullscreen_cooldown_timer = QTimer(self)
        self._fullscreen_cooldown_timer.setSingleShot(True)
        self._fullscreen_cooldown_timer.setInterval(1000)
        self._fullscreen_cooldown_timer.timeout.connect(self._on_fullscreen_cooldown_end)

        self._build_ui()
        self._connect_actions()
        self._history.push(self._doc)

        if path:
            self._open(path)
            self._video_path = _find_video_for_subtitle(path)
            if not self._video_hash and self._video_path:
                self._video_hash = compute_sha256(self._video_path) or ""
            if self._video_duration_s <= 0 and self._video_path:
                self._video_duration_s = _get_duration(self._video_path)

        self._update_mode()
        self._sync_nav_to_doc()
        self._sync_video_to_doc()

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # Toolbar (auto-hidden unless mouse near top of dialog)
        self._toolbar_widget = QWidget()
        self._toolbar_widget.setMouseTracking(True)
        self._toolbar_effect = QGraphicsOpacityEffect(self._toolbar_widget)
        self._toolbar_effect.setOpacity(0.0)
        self._toolbar_widget.setGraphicsEffect(self._toolbar_effect)
        toolbar = QHBoxLayout(self._toolbar_widget)
        self._save_btn = QPushButton(_("Guardar"))
        self._save_btn.clicked.connect(self._on_save)
        toolbar.addWidget(self._save_btn)

        self._save_as_btn = QPushButton(_("Guardar como..."))
        self._save_as_btn.clicked.connect(self._on_save_as)
        toolbar.addWidget(self._save_as_btn)

        self._search_btn = QPushButton(_("Buscar"))
        self._search_btn.clicked.connect(self._on_search)
        toolbar.addWidget(self._search_btn)

        self._compartir_btn = QPushButton(_("Compartir"))
        self._compartir_btn.clicked.connect(self._on_compartir)
        self._update_compartir_btn()
        CLIENTE.loginFinished.connect(self._on_login_changed)
        toolbar.addWidget(self._compartir_btn)

        toolbar.addStretch()

        self._expert_toggle = QCheckBox(_("Modo Experto"))
        self._expert_toggle.setChecked(self._expert_mode)
        self._expert_toggle.toggled.connect(self._on_expert_toggled)
        toolbar.addWidget(self._expert_toggle)

        self._close_btn = QPushButton(_("Cerrar"))
        self._close_btn.clicked.connect(self._on_close)
        toolbar.addWidget(self._close_btn)

        self._toolbar_anim = None
        self._toolbar_poll = QTimer(self)
        self._toolbar_poll.setInterval(100)
        self._toolbar_poll.timeout.connect(self._poll_toolbar)
        self._toolbar_poll.start()

        layout.addWidget(self._toolbar_widget)

        # Stacked widget with two modes
        self._stack = QStackedWidget()

        # Page 0: Easy Mode (video + navigation)
        self._easy_page = QWidget()
        easy_layout = QVBoxLayout(self._easy_page)
        easy_layout.setContentsMargins(0, 0, 0, 0)

        self._easy_splitter = QSplitter(Qt.Vertical)
        self._easy_splitter.setHandleWidth(8)
        self._easy_splitter.setStyleSheet(
            "QSplitter::handle { background-color: #555; border: 1px solid #333; }"
        )

        self._video_player = VideoPlayerWidget()
        self._video_player.setMinimumHeight(150)
        self._easy_splitter.addWidget(self._video_player)

        self._nav = SubtitleNavigationWidget()
        self._nav.setMinimumHeight(24)
        self._easy_splitter.addWidget(self._nav)

        self._easy_splitter.setStretchFactor(0, 3)
        self._easy_splitter.setStretchFactor(1, 1)

        self._easy_splitter.splitterMoved.connect(self._on_easy_splitter_moved)

        saved = get_config("editor.easy_splitter_sizes", None)
        if saved and len(saved) == 2:
            self._easy_splitter.setSizes(saved)
        else:
            self._easy_splitter.setSizes([520, 140])

        QTimer.singleShot(0, self._on_easy_splitter_moved)

        easy_layout.addWidget(self._easy_splitter)
        self._stack.addWidget(self._easy_page)

        # Page 1: Expert Mode (table + preview)
        self._expert_page = QWidget()
        expert_layout = QVBoxLayout(self._expert_page)
        expert_layout.setContentsMargins(0, 0, 0, 0)

        self._model = SubtitleTableModel(self._doc, self)
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QHeaderView.SelectRows)
        self._table.setSelectionMode(QHeaderView.SingleSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setAlternatingRowColors(True)

        self._preview = QTextBrowser()
        self._preview.setReadOnly(True)
        self._preview.setStyleSheet(
            "QTextBrowser { background: #1e1e1e; color: #fff; font-family: 'Segoe UI', Arial; font-size: 11pt; "
            "border: 1px solid #333; padding: 12px; }"
        )

        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.addWidget(self._table)
        self._splitter.addWidget(self._preview)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 2)
        self._splitter.setHandleWidth(4)
        expert_layout.addWidget(self._splitter)

        self._stack.addWidget(self._expert_page)
        layout.addWidget(self._stack, 1)

        # Keyboard shortcuts (always available)
        self._undo_shortcut = QShortcut(QKeySequence.Undo, self)
        self._undo_shortcut.activated.connect(self._on_undo)
        self._redo_shortcut = QShortcut(QKeySequence.Redo, self)
        self._redo_shortcut.activated.connect(self._on_redo)

        # Easy Mode signal connections (one-time, always valid)
        self._video_player.subtitleClickRequested.connect(self._on_overlay_edit_started)
        self._video_player.editStarted.connect(self._on_before_edit)
        self._video_player.editCommitted.connect(self._on_overlay_edit_committed)
        self._video_player.positionChanged.connect(self._on_player_position_changed)
        self._video_player.playbackStateChanged.connect(self._on_video_playback_changed)
        self._video_player.aboutToTogglePlay.connect(self._on_about_to_toggle_play)
        self._video_player.installEventFilter(self)
        self._video_player._view.viewport().installEventFilter(self)
        self._nav.seekRequested.connect(self._on_nav_seek_requested)
        self._nav.subtitleTextChanged.connect(self._on_nav_text_changed)
        self._nav.editStarted.connect(self._on_before_edit)
        self._nav.fragmentAdded.connect(self._on_nav_fragment_added)

        # Toast overlay (dialog-level, raised above stack)
        self._toast = QLabel(self)
        self._toast.raise_()
        self._toast.setAlignment(Qt.AlignCenter)
        self._toast.setStyleSheet("""
            QLabel {
                background: rgba(0, 0, 0, 180);
                color: #00ff88;
                font-size: 16px;
                padding: 8px 20px;
                border-radius: 6px;
            }
        """)
        self._toast.setFixedHeight(36)
        self._toast.hide()

    def _connect_actions(self) -> None:
        self._model.beforeEdit.connect(self._on_before_edit)
        self._model.dataChanged.connect(self._on_data_changed)
        self._model.dataChanged.connect(self._update_preview)

    # ── File operations ────────────────────────────────────────────────

    def _open(self, path: str) -> None:
        fmt = detect_format(path)
        loader = _LOADERS.get(fmt, load_srt)
        try:
            self._doc = loader(path)
            self._model = SubtitleTableModel(self._doc, self)
            self._table.setModel(self._model)
            self._connect_actions()
            self._history.clear()
            self._history.push(self._doc)
            self._update_title()
            self._update_preview()
        except Exception as e:
            QMessageBox.critical(self, _("Error"), f"{_('No se pudo abrir')}: {e}")

    def _on_save(self) -> None:
        if self._doc.path:
            self._save_to(self._doc.path)
        else:
            self._on_save_as()

    def _on_save_as(self) -> None:
        path, _filt = QFileDialog.getSaveFileName(
            self, _("Guardar como..."),
            str(self._doc.path) if self._doc.path else "",
            _("Subtitulos (*.srt *.vtt *.ass);;Todos (*.*)"),
        )
        if path:
            self._save_to(Path(path))

    def _save_to(self, path: Path) -> None:
        fmt = detect_format(str(path))
        saver = _SAVERS.get(fmt, save_srt)
        try:
            saver(self._doc, str(path))
            self._update_title()
            self._show_toast(_("Guardado"))
        except Exception as e:
            QMessageBox.critical(self, _("Error"), f"{_('No se pudo guardar')}: {e}")

    def _on_close(self) -> None:
        if self._doc.modified:
            ret = QMessageBox.question(
                self, _("Cambios sin guardar"),
                _("Hay cambios sin guardar. Guardar antes de cerrar?"),
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            )
            if ret == QMessageBox.Save:
                self._on_save()
            elif ret == QMessageBox.Cancel:
                return
        self.accept()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_splitter_state()
        self._on_close()

    def _save_splitter_state(self) -> None:
        sizes = list(self._easy_splitter.sizes())
        set_config("editor.easy_splitter_sizes", sizes)

    # ── Toolbar auto-hide ──────────────────────────────────────────────

    def _fade_toolbar(self, target_opacity: float) -> None:
        if target_opacity > 0.5 and not self._toolbar_widget.isVisible():
            self._toolbar_widget.setVisible(True)
            self._toolbar_effect.setOpacity(0.0)
        if self._toolbar_anim:
            self._toolbar_anim.stop()
            self._toolbar_anim.deleteLater()
            self._toolbar_anim = None
        self._toolbar_anim = QPropertyAnimation(self._toolbar_effect, b"opacity")
        self._toolbar_anim.setDuration(300)
        self._toolbar_anim.setStartValue(self._toolbar_effect.opacity())
        self._toolbar_anim.setEndValue(target_opacity)
        self._toolbar_anim.finished.connect(self._on_toolbar_fade_finished)
        self._toolbar_anim.start()

    def _on_toolbar_fade_finished(self) -> None:
        self._toolbar_anim.deleteLater()
        self._toolbar_anim = None
        if self._toolbar_effect.opacity() < 0.1:
            self._toolbar_widget.setVisible(False)

    def _poll_toolbar(self) -> None:
        gp = QCursor.pos()
        lp = self.mapFromGlobal(gp)
        near_top = self.rect().contains(lp) and lp.y() < 50
        in_easy = self._stack.currentIndex() == 0

        # Sync video controls auto-hide (same rules as toolbar)
        if not self._expert_mode and in_easy:
            self._video_player.set_auto_hide_enabled(self.isMaximized() or self.isFullScreen())

        # Expert mode: toolbar always visible, no auto-hide
        if self._expert_mode:
            if self._toolbar_effect.opacity() < 0.5:
                self._fade_toolbar(1.0)
            return

        # Fullscreen entry: maximized + both UIs hidden + Easy Mode
        if (self.isMaximized() and not self.isFullScreen()
                and self._toolbar_effect.opacity() < 0.5
                and not self._video_player.is_controls_visible()
                and not self._fullscreen_cooldown
                and in_easy):
            self._enter_fullscreen()
            return

        # Fullscreen exit: cursor at very top
        if self.isFullScreen() and near_top and not self._fullscreen_cooldown:
            self._exit_fullscreen()
            return

        # Auto-hide only when maximized (not in windowed mode)
        if not self.isMaximized() and not self.isFullScreen():
            if self._toolbar_effect.opacity() < 0.5:
                self._fade_toolbar(1.0)
            return

        # Normal toolbar show/hide (maximized or fullscreen)
        if near_top and self._toolbar_effect.opacity() < 0.5:
            self._fade_toolbar(1.0)
        elif not near_top and self._toolbar_effect.opacity() > 0.5:
            self._fade_toolbar(0.0)

    def _enter_fullscreen(self) -> None:
        self._fullscreen_cooldown = True
        self._fullscreen_cooldown_timer.start(1000)
        self.showFullScreen()

    def _exit_fullscreen(self) -> None:
        self._fullscreen_cooldown = True
        self._fullscreen_cooldown_timer.start(500)
        self._fade_toolbar(1.0)
        self._video_player.show_controls()
        self.showMaximized()

    def _on_fullscreen_cooldown_end(self) -> None:
        self._fullscreen_cooldown = False

    def hideEvent(self, event) -> None:
        self._toolbar_poll.stop()
        super().hideEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._toolbar_widget.setVisible(True)
        self._toolbar_effect.setOpacity(1.0)
        self._toolbar_poll.start()

    # ── Undo / Redo ────────────────────────────────────────────────────

    def _on_before_edit(self, *_) -> None:
        self._history.push(self._doc)

    def _on_data_changed(self) -> None:
        self._update_title()

    def _on_undo(self) -> None:
        restored = self._history.undo(self._doc)
        if restored is not None:
            self._doc = restored
            self._refresh_model()
            self._update_preview()
            self._sync_nav_to_doc()
            self._sync_video_to_doc()

    def _on_redo(self) -> None:
        restored = self._history.redo(self._doc)
        if restored is not None:
            self._doc = restored
            self._refresh_model()
            self._update_preview()
            self._sync_nav_to_doc()
            self._sync_video_to_doc()

    # ── Search ─────────────────────────────────────────────────────────

    def _on_search(self) -> None:
        dlg = SearchDialog(self._doc, self)
        dlg.exec()

    def _on_compartir(self) -> None:
        if not self._subtitle_path:
            return
        ruta_srt = Path(self._subtitle_path)
        if not ruta_srt.exists():
            return

        normalizacion_habilitada = get_config("comunidad.normalizacion_habilitada", True)
        puede_compartir_metadata = (
            normalizacion_habilitada
            and get_config("comunidad.share_consent_given", False)
        )

        # Confirmation dialogs based on config state
        msgs = []
        if not get_config("comunidad.subir_automaticamente", True):
            msgs.append(
                "Tienes la subida automatica desactivada.\n"
                "Este sera un envio unico."
            )
        if not puede_compartir_metadata and normalizacion_habilitada:
            msgs.append(
                "Compartir metadatos esta desactivado.\n"
                "Este subtitulo se compartira SIN metadatos del video."
            )
        if msgs:
            reply = QMessageBox.question(
                self, _("Compartir subtitulo"),
                "\n\n".join(msgs) + "\n\n" + _("Deseas continuar?"),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        # Compute metadata locally if normalization enabled
        parsed = {}
        if normalizacion_habilitada:
            file_stem = (
                Path(self._video_path).stem
                if self._video_path
                else ruta_srt.stem
            )
            parsed = parse_video_filename(file_stem)

        video_hash = self._video_hash or compute_sha256(ruta_srt) or ""
        video_nombre = (
            Path(self._video_path).name
            if self._video_path
            else ruta_srt.stem
        )
        duracion_seg = (
            self._video_duration_s
            if self._video_duration_s > 0
            else max((e.end_ms for e in self._doc.entries), default=0) / 1000.0
        )
        tamano_bytes = ruta_srt.stat().st_size
        word_count = sum(len(e.text.split()) for e in self._doc.entries)

        resultado = CLIENTE.compartir_subtitulo(
            ruta_srt=ruta_srt,
            video_hash=video_hash,
            video_nombre=video_nombre,
            duracion_seg=duracion_seg,
            tamano_bytes=tamano_bytes,
            idioma="es",
            es_revision_manual=True,
            word_count=word_count,
            avg_confidence=0.0,
            season=parsed.get("season") if puede_compartir_metadata else None,
            episode=parsed.get("episode") if puede_compartir_metadata else None,
            year=parsed.get("year") if puede_compartir_metadata else None,
            title_clean=parsed.get("title_clean") if puede_compartir_metadata else None,
            resolution=parsed.get("resolution") if puede_compartir_metadata else None,
            release_group=parsed.get("release_group") if puede_compartir_metadata else None,
            source_type=parsed.get("source") if puede_compartir_metadata else None,
            parse_confidence=parsed.get("confidence") if puede_compartir_metadata else None,
            normalization_version=parsed.get("normalization_version") if puede_compartir_metadata else None,
        )
        if resultado:
            self._video_player.show_toast(_("Subtitulo compartido exitosamente"), persistente=False)
        else:
            self._video_player.show_toast(_("Error al compartir subtitulo"), persistente=False)

    def _update_compartir_btn(self) -> None:
        visible = CLIENTE.is_logged_in() and self._share_candidate
        self._compartir_btn.setVisible(visible)

    def _on_login_changed(self, success: bool) -> None:
        self._update_compartir_btn()

    # ── Mode switching ─────────────────────────────────────────────────

    def _on_expert_toggled(self, checked: bool) -> None:
        self._expert_mode = checked
        set_config("editor.expert_mode", checked)
        if self._expert_mode:
            self._stack.setCurrentIndex(1)
            self._update_preview()
        else:
            self._stack.setCurrentIndex(0)
            self._sync_nav_to_doc()
            self._sync_video_to_doc()
            self._on_easy_splitter_moved()
            if not self._video_path:
                self._video_player.load_video("")
                self._video_player.show_toast(
                    "No se encontr\u00f3 video para este subt\u00edtulo", persistente=True
                )

    def _update_mode(self) -> None:
        if self._expert_mode:
            self._stack.setCurrentIndex(1)
            self._update_preview()
        else:
            self._stack.setCurrentIndex(0)
            self._on_easy_splitter_moved()
            if self._video_path:
                self._video_player.load_video(self._video_path)
                QTimer.singleShot(500, self._video_player.play)

    def _sync_nav_to_doc(self) -> None:
        fresh = [e.clone() for e in self._doc.entries]
        self._nav.load_entries(fresh)

    def _sync_video_to_doc(self) -> None:
        self._video_player.load_subtitles(self._doc.entries)

    def _on_easy_splitter_moved(self) -> None:
        self._nav.set_collapsed(self._nav.height() < 30)

    # ── Easy Mode signal handlers ──────────────────────────────────────

    def _on_overlay_edit_started(self, index: int) -> None:
        self._video_player.start_editing()

    def _on_overlay_edit_committed(self, index: int, text: str) -> None:
        self._doc.modified = True
        self._sync_nav_to_doc()
        self._update_title()
        self._auto_save()

    def _on_player_position_changed(self, pos_ms: int) -> None:
        for e in self._doc.entries:
            if e.start_ms <= pos_ms < e.end_ms:
                self._nav.highlight_current(e.index)
                break

    def _on_nav_seek_requested(self, start_ms: int) -> None:
        self._video_player.set_position(start_ms)

    def _auto_save(self) -> None:
        if not self._doc.path or not self._doc.modified:
            return
        fmt = detect_format(str(self._doc.path))
        saver = _SAVERS.get(fmt, save_srt)
        try:
            saver(self._doc, str(self._doc.path))
            self._doc.modified = True
        except Exception:
            pass

    def _on_nav_text_changed(self, index: int, text: str) -> None:
        for e in self._doc.entries:
            if e.index == index:
                if e.text == text:
                    return
                e.text = text
                break
        self._doc.modified = True
        self._sync_video_to_doc()
        self._update_title()
        self._auto_save()
        self._show_toast(_("Guardado"))

    def _on_about_to_toggle_play(self) -> None:
        if not self._expert_mode:
            self._nav.commit_edit()

    def _on_video_playback_changed(self) -> None:
        if not self._expert_mode:
            self._nav.commit_edit()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if not self._expert_mode and self._nav.is_editing():
                self._nav.commit_edit()
        return super().eventFilter(obj, event)

    def _on_nav_fragment_added(self, _) -> None:
        pos = self._video_player.current_position()
        new_entry = SubtitleEntry(
            index=0,
            start_ms=pos,
            end_ms=pos + 3000,
            text="Nuevo fragmento",
        )
        self._history.push(self._doc)
        insert_entry(self._doc, new_entry)
        self._sync_nav_to_doc()
        self._sync_video_to_doc()
        self._update_title()
        self._auto_save()
        for e in self._doc.entries:
            if e.start_ms == pos:
                self._nav.highlight_current(e.index)
                break

    # ── Toast ───────────────────────────────────────────────────────────

    def _show_toast(self, text: str, persistente: bool = False) -> None:
        self._toast.setText(text)
        self._toast.show()
        self._toast.raise_()
        self._reposition_toast()
        self._toast.raise_()
        if persistente:
            return
        self._toast._toast_timer = getattr(self._toast, '_toast_timer', None)
        if self._toast._toast_timer:
            self._toast._toast_timer.stop()
        self._toast._toast_timer = QTimer(self._toast)
        self._toast._toast_timer.setSingleShot(True)
        self._toast._toast_timer.setInterval(3000)
        self._toast._toast_timer.timeout.connect(self._toast.hide)
        self._toast._toast_timer.start()

    def _reposition_toast(self) -> None:
        self._toast.adjustSize()
        x = (self.width() - self._toast.width()) // 2
        y = self.height() - self._toast.height() - 60
        self._toast.move(x, y)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reposition_toast()

    # ── Expert Mode helpers (unchanged) ───────────────────────────────

    def _update_preview(self) -> None:
        if not self._expert_mode:
            return
        lines = []
        for e in self._doc.entries:
            start = _ms_to_str(e.start_ms)
            end = _ms_to_str(e.end_ms)
            text = e.text.replace("\n", "<br>")
            lines.append(
                f"<p style='margin: 8px 0;'><b>{start} \u2192 {end}</b><br>{text}</p>"
            )
        html = (
            "<div style='line-height: 1.5;'>"
            + "".join(lines)
            + "</div>"
        )
        self._preview.setHtml(html)

    def _update_title(self) -> None:
        name = self._doc.path.name if self._doc.path else _("sin titulo")
        flag = " *" if self._doc.modified else ""
        self.setWindowTitle(f"{_('Editor de subtitulos')} \u2014 {name}{flag}")

    def _refresh_model(self) -> None:
        self._model.beginResetModel()
        self._model = SubtitleTableModel(self._doc, self)
        self._table.setModel(self._model)
        self._connect_actions()
        self._model.endResetModel()
        self._update_title()
        self._update_preview()

    def _select_entry(self, index: int) -> None:
        for row, e in enumerate(self._doc.entries):
            if e.index == index:
                idx = self._model.index(row, 0)
                self._table.selectRow(row)
                self._table.scrollTo(idx)
                break

    # ── Hotkeys (Easy Mode Escape) ─────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self._exit_fullscreen()
                event.accept()
                return
            if self._expert_mode:
                if self._table.state() == QAbstractItemView.EditingState:
                    self._table.clearFocus()
                    event.accept()
                    return
            else:
                if self._nav.is_editing():
                    self._nav.commit_edit()
                    event.accept()
                    return
            self._on_close()
            event.accept()
            return
        if event.key() == Qt.Key_Space:
            if not self._expert_mode and self._nav.is_editing():
                nav_rect = self._nav.rect()
                cursor_in_nav = nav_rect.contains(
                    self._nav.mapFromGlobal(QCursor.pos())
                )
                if cursor_in_nav:
                    super().keyPressEvent(event)
                    return
            self._video_player._toggle_play()
            event.accept()
            return
        super().keyPressEvent(event)
