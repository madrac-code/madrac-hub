"""
Widget factory for MUI.

Creates PySide6 widgets from JSON descriptors.
All methods MUST be called from the Qt main thread.

Supported widget types (Phase 1):
  label          — static text
  button         — triggers an MCP tool or internal action
  table          — read-only tabular data
  audio_player   — play/pause/seek for a workspace audio file
  waveform       — visual waveform display (read-only)
  segment_selector — list of segments with timestamps, selectable
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QSlider, QSizePolicy,
)

logger = logging.getLogger(__name__)

# Whitelist of allowed action types
_INTERNAL_ACTIONS = {"play_segment", "record_segment", "close_window"}


def validate_action(action: dict) -> bool:
    """
    Validate a button action descriptor.
    action = {"tool": "tool_name", "params": {...}}
    or       {"internal": "play_segment", "params": {...}}
    """
    if not isinstance(action, dict):
        return False
    if "tool" in action:
        return isinstance(action["tool"], str) and len(action["tool"]) > 0
    if "internal" in action:
        return action["internal"] in _INTERNAL_ACTIONS
    return False


def create_widget(
    descriptor: dict[str, Any],
    on_event: Callable,
    window_id: str,
) -> QWidget | None:
    """
    Create a single widget from a descriptor dict.

    descriptor must have "type" and "id" fields.
    on_event(event_type, widget_id, payload) is called on interaction.
    """
    wtype = descriptor.get("type", "")
    wid = descriptor.get("id", f"widget_{id(descriptor)}")

    try:
        if wtype == "label":
            return _make_label(descriptor)

        elif wtype == "button":
            return _make_button(descriptor, on_event, window_id, wid)

        elif wtype == "table":
            return _make_table(descriptor)

        elif wtype == "segment_selector":
            return _make_segment_selector(descriptor, on_event, wid)

        elif wtype == "audio_player":
            return _make_audio_player(descriptor, on_event, wid)

        elif wtype == "waveform":
            return _make_waveform_placeholder(descriptor)

        else:
            logger.warning("Unknown widget type: %s", wtype)
            return None

    except Exception as e:
        logger.error("Error creating widget %s (%s): %s", wid, wtype, e)
        return None


def _make_label(d: dict) -> QLabel:
    label = QLabel(d.get("text", ""))
    if d.get("bold"):
        font = label.font()
        font.setBold(True)
        label.setFont(font)
    if d.get("align") == "center":
        label.setAlignment(Qt.AlignCenter)
    return label


def _make_button(
    d: dict,
    on_event: Callable,
    window_id: str,
    wid: str,
) -> QPushButton:
    btn = QPushButton(d.get("text", "Button"))
    action = d.get("action", {})

    if not validate_action(action):
        logger.warning("Button %s has invalid action — disabling", wid)
        btn.setEnabled(False)
        return btn

    def _clicked():
        on_event("button_click", wid, {"action": action})

    btn.clicked.connect(_clicked)
    return btn


def _make_table(d: dict) -> QTableWidget:
    columns = d.get("columns", [])
    rows = d.get("rows", [])
    table = QTableWidget(len(rows), len(columns))
    table.setHorizontalHeaderLabels(columns)
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            item = QTableWidgetItem(str(cell))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            table.setItem(r, c, item)
    table.resizeColumnsToContents()
    return table


def _make_segment_selector(d: dict, on_event: Callable, wid: str) -> QListWidget:
    lst = QListWidget()
    segments = d.get("segments", [])
    for seg in segments:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        text = seg.get("text", "")
        label = f"[{start:.1f}s → {end:.1f}s] {text[:60]}"
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, seg)
        lst.addItem(item)

    def _selected():
        current = lst.currentItem()
        if current:
            on_event("segment_selected", wid,
                     {"segment": current.data(Qt.UserRole)})

    lst.currentItemChanged.connect(lambda *_: _selected())
    return lst


def _make_audio_player(d: dict, on_event: Callable, wid: str) -> QWidget:
    """Simple audio player: play/pause button + position slider."""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    btn = QPushButton("▶ Play")
    btn.setFixedWidth(80)
    slider = QSlider(Qt.Horizontal)
    slider.setRange(0, 1000)

    _state = {"playing": False}

    def _toggle():
        _state["playing"] = not _state["playing"]
        btn.setText("⏸ Pause" if _state["playing"] else "▶ Play")
        on_event("audio_position",  wid,
                 {"playing": _state["playing"],
                  "position": slider.value() / 1000})

    btn.clicked.connect(_toggle)
    layout.addWidget(btn)
    layout.addWidget(slider)
    return container


def _make_waveform_placeholder(d: dict) -> QLabel:
    """Phase 1: waveform is a labeled placeholder."""
    label = QLabel(f"〜 Waveform: {d.get('audio_path', 'no audio')} 〜")
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet(
        "background: #1a1a2e; color: #4ecca3; "
        "border: 1px solid #4ecca3; padding: 8px;"
    )
    label.setMinimumHeight(80)
    return label