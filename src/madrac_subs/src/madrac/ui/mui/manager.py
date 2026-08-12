"""
UIManager — central coordinator for MUI windows.

Lives in the Qt main thread. MCP tools communicate via
QMetaObject.invokeMethod to ensure thread safety.

Always active: started in MainWindow.__init__.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QObject, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QWidget, QLabel, QDialogButtonBox,
)

from .events import WindowEventQueue, UIEvent
from .factory import create_widget

logger = logging.getLogger(__name__)

MAX_WINDOWS = 5
AUTO_CLOSE_SECONDS = 600  # 10 minutes of inactivity

WORKSPACE_ROOT = Path.home() / ".cache" / "madrac" / "workspace" / "jobs"


class MUIWindow(QDialog):
    """A single procedurally-created MUI window."""

    def __init__(
        self,
        window_id: str,
        title: str,
        job_id: str | None,
        event_queue: WindowEventQueue,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.window_id = window_id
        self.job_id = job_id
        self._event_queue = event_queue
        self._widget_map: dict[str, QWidget] = {}

        self.setWindowTitle(title)
        self.setMinimumSize(400, 300)
        self._layout = QVBoxLayout(self)

    def add_widget(self, descriptor: dict, widget: QWidget) -> None:
        wid = descriptor.get("id", str(id(widget)))
        self._widget_map[wid] = widget
        self._layout.addWidget(widget)

    def emit_event(self, event_type: str, widget_id: str,
                   payload: dict) -> None:
        event = UIEvent(
            window_id=self.window_id,
            event_type=event_type,
            widget_id=widget_id,
            payload=payload,
        )
        self._event_queue.put(event)

    def closeEvent(self, event):
        self.emit_event("window_closed", "window", {})
        super().closeEvent(event)


class UIManager(QObject):
    """
    Central manager for all MUI windows.
    Always active — started in MainWindow.__init__.
    Thread-safe: MCP tools call public methods via invokeMethod.
    """

    # Signals for thread-safe cross-thread calls
    _create_window_signal = Signal(str, str, str, str, str)
    _update_widget_signal = Signal(str, str, str)
    _close_window_signal = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._windows: dict[str, MUIWindow] = {}
        self._event_queues: dict[str, WindowEventQueue] = {}
        # window_ids emitted but not yet materialized on the Qt thread —
        # needed to enforce MAX_WINDOWS from the MCP thread (async creation)
        self._pending: set[str] = set()
        self._result_cache: dict[str, Any] = {}

        # Connect signals to slots (all run in Qt main thread)
        self._create_window_signal.connect(self._slot_create_window)
        self._update_widget_signal.connect(self._slot_update_widget)
        self._close_window_signal.connect(self._slot_close_window)

        # Auto-close timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_inactive_windows)
        self._timer.start(60_000)  # check every minute

        logger.info("UIManager started — MUI Protocol active")

    # ── Public API (called from MCP tools via invokeMethod) ──────────────

    def create_window(
        self,
        title: str,
        job_id: str,
        widgets: list[dict],
        keybindings: dict[str, str],
    ) -> dict:
        """Create a new MUI window. Thread-safe."""
        if len(self._windows) + len(self._pending) >= MAX_WINDOWS:
            return {"error": f"Max {MAX_WINDOWS} windows open simultaneously"}

        window_id = str(uuid.uuid4())[:8]
        # Must exist before the slot runs (slot may run synchronously on a
        # DirectConnection when called from the Qt thread itself).
        self._event_queues[window_id] = WindowEventQueue(window_id)
        self._pending.add(window_id)
        # Signal emission from another thread is auto-queued to the Qt main
        # thread (QueuedConnection semantics of Qt signals).
        self._create_window_signal.emit(
            window_id,
            title,
            job_id or "",
            json.dumps(keybindings),
            json.dumps(widgets),
        )
        return {"window_id": window_id, "status": "created"}

    def get_window_events(self, window_id: str) -> dict:
        """Drain pending events for a window. Thread-safe (queue is safe)."""
        if window_id not in self._event_queues:
            return {"error": f"Window {window_id} not found"}
        events = self._event_queues[window_id].drain()
        return {
            "window_id": window_id,
            "events": [
                {
                    "event_type": e.event_type,
                    "widget_id": e.widget_id,
                    "payload": e.payload,
                    "timestamp": e.timestamp,
                }
                for e in events
            ],
        }

    def list_windows(self) -> dict:
        """List open windows with their status."""
        return {
            "windows": [
                {
                    "window_id": wid,
                    "title": w.windowTitle(),
                    "job_id": w.job_id,
                    "visible": w.isVisible(),
                    "inactive_seconds": self._event_queues[wid]
                        .seconds_since_activity()
                        if wid in self._event_queues else 0,
                }
                for wid, w in self._windows.items()
            ]
        }

    def close_window(self, window_id: str) -> dict:
        """Close a window by ID. Thread-safe."""
        if window_id not in self._windows:
            return {"error": f"Window {window_id} not found"}
        self._close_window_signal.emit(window_id)
        return {"success": True, "window_id": window_id}

    def update_widget(
        self, window_id: str, widget_id: str, props: dict
    ) -> dict:
        """Update a widget's properties. Thread-safe."""
        if window_id not in self._windows:
            return {"error": f"Window {window_id} not found"}
        self._update_widget_signal.emit(window_id, widget_id, json.dumps(props))
        return {"success": True}

    # ── Qt Slots (run in main thread) ────────────────────────────────────

    @Slot(str, str, str, str, str)
    def _slot_create_window(
        self,
        window_id: str,
        title: str,
        job_id: str,
        keybindings_json: str,
        widgets_json: str,
    ) -> None:
        self._pending.discard(window_id)
        if window_id in self._windows:
            return

        eq = self._event_queues.setdefault(
            window_id, WindowEventQueue(window_id)
        )
        win = MUIWindow(
            window_id=window_id,
            title=title,
            job_id=job_id or None,
            event_queue=eq,
            parent=None,
        )

        widgets_desc = json.loads(widgets_json)
        for desc in widgets_desc:
            widget = create_widget(
                desc,
                on_event=win.emit_event,
                window_id=window_id,
            )
            if widget:
                win.add_widget(desc, widget)

        self._windows[window_id] = win
        win.show()

        # Persist ui_state.json if job_id provided
        if job_id:
            self._save_ui_state(job_id, window_id, title,
                                widgets_desc, json.loads(keybindings_json))

        logger.info("MUI window created: %s (%s)", window_id, title)

    @Slot(str)
    def _slot_close_window(self, window_id: str) -> None:
        win = self._windows.pop(window_id, None)
        if win:
            win.close()
            win.deleteLater()
        self._event_queues.pop(window_id, None)
        logger.info("MUI window closed: %s", window_id)

    @Slot(str, str, str)
    def _slot_update_widget(
        self, window_id: str, widget_id: str, props_json: str
    ) -> None:
        win = self._windows.get(window_id)
        if not win:
            return
        props = json.loads(props_json)
        widget = win._widget_map.get(widget_id)
        if not widget:
            logger.warning("Widget %s not found in window %s",
                           widget_id, window_id)
            return
        # Apply supported prop updates
        if "text" in props and hasattr(widget, "setText"):
            widget.setText(props["text"])
        if "enabled" in props and hasattr(widget, "setEnabled"):
            widget.setEnabled(props["enabled"])

    def _check_inactive_windows(self) -> None:
        """Auto-close windows inactive for AUTO_CLOSE_SECONDS."""
        to_close = [
            wid for wid, eq in self._event_queues.items()
            if eq.seconds_since_activity() > AUTO_CLOSE_SECONDS
        ]
        for wid in to_close:
            logger.info("Auto-closing inactive MUI window: %s", wid)
            self._slot_close_window(wid)

    # ── Internal actions ──────────────────────────────────────────────────

    def play_segment(self, window_id: str, segment: dict) -> dict:
        """
        Play a segment's audio from the workspace.
        Finds audio_whisper.wav and plays from start to end timestamp.
        """
        win = self._windows.get(window_id)
        if not win or not win.job_id:
            return {"error": "Window or job_id not found"}

        ws_path = WORKSPACE_ROOT / win.job_id
        audio_path = ws_path / "audio_whisper.wav"
        if not audio_path.exists():
            return {"error": f"No audio found at {audio_path}"}

        start_s = segment.get("start", 0)
        end_s = segment.get("end", 0)

        try:
            import sounddevice as sd
            import soundfile as sf
            data, sr = sf.read(str(audio_path))
            start_frame = int(start_s * sr)
            end_frame = int(end_s * sr)
            chunk = data[start_frame:end_frame]
            sd.play(chunk, sr)
            return {"success": True,
                    "playing": f"{start_s:.1f}s → {end_s:.1f}s"}
        except Exception as e:
            return {"error": str(e)}

    def record_segment(
        self, window_id: str, segment_id: int, duration_s: float
    ) -> dict:
        """
        Record mic audio for a segment duration.
        Uses sd.rec() + resample to 16kHz (avoids LLAVE-005 blocking issue).
        scipy.signal.resample is preferred; falls back to a numpy linear
        interpolation when scipy is not bundled (e.g. frozen builds that
        exclude scipy to keep the exe small).
        """
        try:
            import sounddevice as sd
            import numpy as np

            # Record at device native rate
            native_sr = int(sd.query_devices(
                kind='input')['default_samplerate'])
            frames = int(duration_s * native_sr)
            recording = sd.rec(frames, samplerate=native_sr,
                               channels=1, dtype='float32')
            sd.wait()

            # Resample to 16kHz for consistency
            target_sr = 16000
            if native_sr != target_sr:
                num_samples = int(len(recording) * target_sr / native_sr)
                try:
                    from scipy.signal import resample
                    recording = resample(recording, num_samples)
                except ImportError:
                    # numpy-only fallback (linear interpolation)
                    old_x = np.linspace(0, 1, num=len(recording))
                    new_x = np.linspace(0, 1, num=num_samples)
                    recording = np.interp(new_x, old_x,
                                          recording[:, 0])[:, None]

            win = self._windows.get(window_id)
            if not win or not win.job_id:
                return {"error": "Window or job_id not found"}

            ws_path = WORKSPACE_ROOT / win.job_id
            out_path = ws_path / "dubbed" / f"seg_{segment_id:04d}_recorded.wav"
            out_path.parent.mkdir(parents=True, exist_ok=True)

            import soundfile as sf
            sf.write(str(out_path), recording, target_sr)

            return {
                "success": True,
                "segment_id": segment_id,
                "recorded_path": str(out_path),
                "duration_s": duration_s,
            }
        except Exception as e:
            return {"error": str(e)}

    # ── Persistence ───────────────────────────────────────────────────────

    def _save_ui_state(
        self,
        job_id: str,
        window_id: str,
        title: str,
        widgets: list,
        keybindings: dict,
    ) -> None:
        try:
            ws_path = WORKSPACE_ROOT / job_id
            ws_path.mkdir(parents=True, exist_ok=True)
            state = {
                "window_id": window_id,
                "title": title,
                "widgets": widgets,
                "keybindings": keybindings,
                "created_at": time.time(),
            }
            (ws_path / "ui_state.json").write_text(
                json.dumps(state, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning("Could not save ui_state.json: %s", e)