"""Video player widget with subtitle overlay and timeline controls."""

import logging
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QUrl, Signal, QTimer, QPropertyAnimation, QSequentialAnimationGroup, QPauseAnimation, QEvent
from PySide6.QtGui import QKeyEvent, QCursor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QSlider, QLabel, QLineEdit, QGraphicsView,
    QGraphicsScene, QGraphicsProxyWidget, QGraphicsOpacityEffect,
    QFrame, QStyle, QStyleOptionSlider,
)

from ...utils.editor_model import SubtitleEntry
from ..i18n import _

logger = logging.getLogger("madrac.ui.video_player")


def _ms_to_str(ms: int) -> str:
    total = ms // 1000
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    r = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{r:03d}"


class TimelineSlider(QSlider):
    """VLC-style slider: click anywhere to seek."""

    seekRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setRange(0, 0)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            val = self._pixel_to_value(event.position().toPoint().x())
            self.setValue(val)
            self.seekRequested.emit(val)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            val = self._pixel_to_value(event.position().toPoint().x())
            self.seekRequested.emit(val)
        super().mouseMoveEvent(event)

    def _pixel_to_value(self, x: int) -> int:
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        groove = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self)
        if groove.isValid() and groove.width() > 0:
            return QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), x, groove.width())
        return self.value()


class VideoPlayerWidget(QWidget):
    """Media player with subtitle overlay, timeline, and toast."""

    positionChanged = Signal(int)
    durationChanged = Signal(int)
    playbackStateChanged = Signal(object)
    aboutToTogglePlay = Signal()
    subtitleClickRequested = Signal(int)
    editStarted = Signal(int)
    editCommitted = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: List[SubtitleEntry] = []
        self._current_index = -1
        self._editing = False
        self._controls_anim = None
        self._auto_hide_enabled = True

        self._setup_media()
        self._setup_scene()
        self._setup_ui()

        self.setMouseTracking(True)
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.setInterval(2000)
        self._idle_timer.timeout.connect(self._on_controls_idle)

    def _setup_media(self):
        self._media_player = QMediaPlayer(self)
        self._audio_output = QAudioOutput()
        self._audio_output.setVolume(1.0)
        self._media_player.setAudioOutput(self._audio_output)

    def _setup_scene(self):
        self._scene = QGraphicsScene(self)
        self._video_item = QGraphicsVideoItem()
        self._video_item.setZValue(0)
        self._scene.addItem(self._video_item)
        self._media_player.setVideoOutput(self._video_item)

        self._view = QGraphicsView(self._scene)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setFrameShape(QFrame.NoFrame)
        self._view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        # Create both overlays BEFORE adding to scene / installing event filters
        self._overlay_label = QLabel()
        self._overlay_label.setAlignment(Qt.AlignCenter)
        self._overlay_label.setWordWrap(True)
        self._overlay_label.setStyleSheet("""
            QLabel {
                background: rgba(0, 0, 0, 160);
                color: white;
                font-size: 22px;
                padding: 10px 18px;
                border-radius: 6px;
            }
        """)

        self._overlay_edit = QLineEdit()
        self._overlay_edit.setAlignment(Qt.AlignCenter)
        self._overlay_edit.setStyleSheet("""
            QLineEdit {
                font-size: 22px; padding: 8px; border-radius: 6px;
            }
        """)
        self._overlay_edit.editingFinished.connect(self._on_edit_finished)

        # Now install event filters and add to scene
        self._overlay_label.installEventFilter(self)
        self._overlay_edit.installEventFilter(self)

        self._overlay_proxy = self._scene.addWidget(self._overlay_label)
        self._overlay_proxy.setZValue(10)
        self._edit_proxy = self._scene.addWidget(self._overlay_edit)
        self._edit_proxy.setZValue(10)
        self._edit_proxy.hide()

    def _setup_ui(self):
        self._play_btn = QPushButton("[Play]")
        self._play_btn.setFixedWidth(80)
        self._play_btn.clicked.connect(self._toggle_play)

        self._slider = TimelineSlider()
        self._slider.seekRequested.connect(self._on_seek_requested)

        self._time_label = QLabel("00:00:00,000 / 00:00:00,000")

        self._controls_container = QWidget()
        self._controls_effect = QGraphicsOpacityEffect(self._controls_container)
        self._controls_effect.setOpacity(1.0)
        self._controls_container.setGraphicsEffect(self._controls_effect)
        controls = QHBoxLayout(self._controls_container)
        controls.addWidget(self._play_btn)
        controls.addWidget(self._slider, 1)
        controls.addWidget(self._time_label)

        self._toast = QLabel()
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
        self._toast_effect = QGraphicsOpacityEffect(self._toast)
        self._toast_effect.setOpacity(0.0)
        self._toast.setGraphicsEffect(self._toast_effect)

        self._video_container = QWidget()
        grid = QGridLayout(self._video_container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self._view, 0, 0)
        grid.addWidget(self._toast, 0, 0, Qt.AlignBottom | Qt.AlignHCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._video_container, 1)
        layout.addWidget(self._controls_container)

        self._media_player.positionChanged.connect(self._on_position_changed)
        self._media_player.durationChanged.connect(self._on_duration_changed)
        self._media_player.errorOccurred.connect(self._on_error)
        self._media_player.mediaStatusChanged.connect(self._on_media_status)
        self._media_player.playbackStateChanged.connect(self._on_media_playback_state_changed)

        self._view.installEventFilter(self)
        self._view.viewport().installEventFilter(self)

    # ── Public API ────────────────────────────────────────────────────

    def load_video(self, path: str) -> bool:
        if not Path(path).exists():
            return False
        self._media_player.setSource(QUrl.fromLocalFile(path))
        return True

    def load_subtitles(self, entries: List[SubtitleEntry]):
        self._entries = entries
        self._current_index = -1

    def set_position(self, ms: int):
        self._media_player.setPosition(ms)

    def seek_relative(self, delta_ms: int):
        pos = self._media_player.position()
        dur = self._media_player.duration()
        if dur <= 0:
            return
        nuevo = max(0, min(pos + delta_ms, dur))
        self._media_player.setPosition(nuevo)

    def toggle_play(self):
        self._toggle_play()

    def play(self):
        self._media_player.play()
        self._play_btn.setText("[Pausa]")
        self.playbackStateChanged.emit(self._media_player.playbackState())

    def pause(self):
        self._media_player.pause()
        self._play_btn.setText(_("[Play]"))
        self.playbackStateChanged.emit(self._media_player.playbackState())

    def is_playing(self) -> bool:
        return self._media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def current_position(self) -> int:
        return self._media_player.position()

    def current_index(self) -> int:
        return self._current_index

    def is_controls_visible(self) -> bool:
        return self._controls_container.isVisible() and self._controls_effect.opacity() > 0.5

    def show_controls(self) -> None:
        self._fade_controls(1.0)

    def set_auto_hide_enabled(self, enabled: bool) -> None:
        self._auto_hide_enabled = enabled
        if not enabled:
            self._idle_timer.stop()
            self._fade_controls(1.0)

    def show_toast(self, text: str, persistente: bool = False):
        self._toast.setText(text)
        self._toast_effect.setOpacity(0.0)
        self._toast.show()
        self._toast.raise_()
        if persistente:
            self._toast_effect.setOpacity(1.0)
            return
        fade_in = QPropertyAnimation(self._toast_effect, b"opacity")
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setDuration(300)
        pause = QPauseAnimation(3000)
        fade_out = QPropertyAnimation(self._toast_effect, b"opacity")
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setDuration(700)
        anim = QSequentialAnimationGroup(self._toast)
        anim.addAnimation(fade_in)
        anim.addAnimation(pause)
        anim.addAnimation(fade_out)
        anim.finished.connect(self._toast.hide)
        anim.finished.connect(anim.deleteLater)
        anim.start()

    def start_editing(self):
        if self._current_index < 0:
            return
        entry = self._entries[self._current_index]
        self._editing = True
        self.editStarted.emit(entry.index)
        self._media_player.pause()
        self._play_btn.setText(_("[Play]"))
        self._overlay_proxy.hide()
        self._overlay_edit.setText(entry.text)
        self._edit_proxy.show()
        self._overlay_edit.setFocus()
        self._overlay_edit.setCursorPosition(len(self._overlay_edit.text()))

    def cancel_edit(self):
        if not self._editing or self._current_index < 0:
            return
        self._editing = False
        self._edit_proxy.hide()
        self._overlay_proxy.show()
        self._overlay_proxy.setZValue(10)
        entry = self._entries[self._current_index]
        self._overlay_label.setText(entry.text)

    def commit_edit(self):
        if not self._editing or self._current_index < 0:
            return
        nuevo_texto = self._overlay_edit.text()
        entry = self._entries[self._current_index]
        if nuevo_texto != entry.text:
            entry.text = nuevo_texto
            self.editCommitted.emit(entry.index, nuevo_texto)
            logger.info("VideoPlayer: texto modificado indice %d", entry.index)
        self._editing = False
        self._edit_proxy.hide()
        self._overlay_proxy.show()
        self._overlay_proxy.setZValue(10)
        self._overlay_label.setText(nuevo_texto)

    # ── Internal slots ────────────────────────────────────────────────

    def _toggle_play(self):
        self.aboutToTogglePlay.emit()
        if self.is_playing():
            self.pause()
        else:
            self.play()

    def _on_seek_requested(self, ms: int):
        self._media_player.setPosition(ms)

    def _on_position_changed(self, pos_ms: int):
        self._slider.setValue(pos_ms)
        dur = self._media_player.duration()
        if dur > 0:
            self._time_label.setText(f"{_ms_to_str(pos_ms)} / {_ms_to_str(dur)}")

        idx = -1
        for i, e in enumerate(self._entries):
            if e.start_ms <= pos_ms < e.end_ms:
                idx = i
                break
        if idx != self._current_index:
            self._current_index = idx
            if idx >= 0:
                self._overlay_label.setText(self._entries[idx].text)
            else:
                self._overlay_label.setText("")
            self._overlay_proxy.setZValue(10)
            self._overlay_proxy.show()

    def _on_duration_changed(self, dur_ms: int):
        self._slider.setRange(0, dur_ms)
        self._time_label.setText(f"00:00:00,000 / {_ms_to_str(dur_ms)}")
        self.durationChanged.emit(dur_ms)

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            logger.info("VideoPlayer: video cargado")
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            err = self._media_player.errorString()
            logger.warning("VideoPlayer: video invalido: %s", err)

    def _on_error(self, error, error_string):
        logger.warning("VideoPlayer: error: %s", error_string)
        self.show_toast(f"Error: {error_string}", persistente=True)

    def _on_media_playback_state_changed(self, state):
        self.playbackStateChanged.emit(state)

    def _on_edit_finished(self):
        self.commit_edit()

    def _on_edit_confirm(self):
        self.commit_edit()
        self.setFocus()
        self._media_player.play()
        self._play_btn.setText("[Pausa]")

    # ── Controls auto-hide ────────────────────────────────────────────

    def _fade_controls(self, target_opacity: float) -> None:
        if target_opacity > 0.5 and not self._controls_container.isVisible():
            self._controls_container.setVisible(True)
            self._controls_effect.setOpacity(0.0)
        if self._controls_anim:
            self._controls_anim.stop()
            self._controls_anim.deleteLater()
            self._controls_anim = None
        self._controls_anim = QPropertyAnimation(self._controls_effect, b"opacity")
        self._controls_anim.setDuration(300)
        self._controls_anim.setStartValue(self._controls_effect.opacity())
        self._controls_anim.setEndValue(target_opacity)
        self._controls_anim.finished.connect(self._on_controls_fade_finished)
        self._controls_anim.start()

    def _on_controls_fade_finished(self) -> None:
        self._controls_anim.deleteLater()
        self._controls_anim = None
        if self._controls_effect.opacity() < 0.1:
            self._controls_container.setVisible(False)

    def _on_controls_idle(self) -> None:
        if self._editing or not self._auto_hide_enabled:
            return
        gp = QCursor.pos()
        lp = self.mapFromGlobal(gp)
        near_bottom = self.rect().contains(lp) and (self.height() - lp.y() < 60)
        if not near_bottom:
            self._fade_controls(0.0)
        else:
            self._idle_timer.start()

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        if not self._auto_hide_enabled:
            return
        self._idle_timer.stop()
        self._idle_timer.start()
        if self._controls_effect.opacity() < 0.5:
            self._fade_controls(1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._idle_timer.stop()
        if self._controls_effect.opacity() < 0.5:
            self._fade_controls(1.0)

    def hideEvent(self, event) -> None:
        self._idle_timer.stop()
        super().hideEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._controls_container.setVisible(True)
        self._controls_effect.setOpacity(1.0)

    # ── Event filter ──────────────────────────────────────────────────

    def eventFilter(self, obj, event):
        if obj is self._overlay_label and event.type() == event.Type.MouseButtonPress:
            if self._current_index >= 0:
                self.subtitleClickRequested.emit(self._current_index)
            return True
        if obj is self._overlay_edit and event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter):
                self.commit_edit()
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    self.setFocus()
                    self._media_player.play()
                    self._play_btn.setText(_("[Pausa]"))
                return True
        if obj is self._view.viewport() and event.type() == event.Type.MouseMove:
            self._idle_timer.stop()
            self._idle_timer.start()
            if self._controls_effect.opacity() < 0.5:
                self._fade_controls(1.0)
            return False
        if obj is self._view.viewport() and event.type() == event.Type.MouseButtonPress:
            scene_pos = self._view.mapToScene(event.position().toPoint())
            items = self._scene.items(scene_pos)
            interactive = any(isinstance(i, QGraphicsProxyWidget) for i in items) if items else False
            if not interactive:
                if self._editing:
                    self.commit_edit()
                self._toggle_play()
                return True
            return False
        if obj is self._view and event.type() == event.Type.KeyPress:
            if self._overlay_edit.hasFocus():
                return False
            self.keyPressEvent(event)
            return True
        if obj is self._view and event.type() == event.Type.Resize:
            self._reposition_overlay()
            return False
        return super().eventFilter(obj, event)

    def _reposition_overlay(self):
        vw = self._view.width()
        vh = self._view.height()
        if vw <= 0 or vh <= 0:
            return
        self._video_item.setSize(self._view.size())
        self._scene.setSceneRect(0, 0, vw, vh)
        margin = 20
        overlay_w = min(vw - margin * 2, 800)
        overlay_h = 80
        x = (vw - overlay_w) // 2
        y = vh - overlay_h - 30
        self._overlay_proxy.setPos(x, y)
        self._overlay_label.resize(overlay_w, overlay_h)
        self._edit_proxy.setPos(x, y)
        self._overlay_edit.resize(overlay_w, overlay_h)

    # ── Hotkeys ───────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent):
        if self._overlay_edit.hasFocus():
            super().keyPressEvent(event)
            return
        jugando = self.is_playing()
        if event.key() == Qt.Key_Space:
            self._toggle_play()
            event.accept()
            return
        if jugando:
            if event.key() == Qt.Key_Left:
                self.seek_relative(-3000)
                event.accept()
                return
            if event.key() == Qt.Key_Right:
                self.seek_relative(3000)
                event.accept()
                return
            if event.key() == Qt.Key_1:
                self.seek_relative(-60000)
                event.accept()
                return
            if event.key() == Qt.Key_3:
                self.seek_relative(60000)
                event.accept()
                return
            if event.key() == Qt.Key_4:
                self.seek_relative(-300000)
                event.accept()
                return
            if event.key() == Qt.Key_6:
                self.seek_relative(300000)
                event.accept()
                return
        super().keyPressEvent(event)
