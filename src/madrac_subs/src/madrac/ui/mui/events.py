"""
Per-window event queue for MUI.

MCP tools read events via get_window_events(window_id).
Qt widgets write events when user interacts.
Thread-safe: Qt main thread writes, MCP daemon thread reads.
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UIEvent:
    """A user interaction event from a MUI window."""
    window_id: str
    event_type: str          # "button_click" | "segment_selected" |
                             # "audio_position" | "window_closed"
    widget_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class WindowEventQueue:
    """Thread-safe event queue for a single window."""

    def __init__(self, window_id: str, maxsize: int = 100) -> None:
        self.window_id = window_id
        self._q: queue.Queue[UIEvent] = queue.Queue(maxsize=maxsize)
        self._last_activity = time.time()

    def put(self, event: UIEvent) -> None:
        """Called from Qt main thread when user interacts."""
        self._last_activity = time.time()
        try:
            self._q.put_nowait(event)
        except queue.Full:
            # Drop oldest event to make room
            try:
                self._q.get_nowait()
            except queue.Empty:
                pass
            self._q.put_nowait(event)

    def drain(self) -> list[UIEvent]:
        """Called from MCP thread to consume all pending events."""
        events = []
        while True:
            try:
                events.append(self._q.get_nowait())
            except queue.Empty:
                break
        return events

    def seconds_since_activity(self) -> float:
        return time.time() - self._last_activity