"""Tests for the MUI Protocol â€” events, factory, UIManager, and MCP tools."""

import os
from unittest.mock import MagicMock

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QPushButton, QTableWidget, QListWidget, QApplication,
)

from madrac.ui.mui.events import UIEvent, WindowEventQueue
from madrac.ui.mui.factory import (
    validate_action, create_widget, normalize_button_action,
)
from madrac.ui.mui.manager import UIManager, MUIWindow, MAX_WINDOWS


def _process_events():
    """Deliver queued invokeMethod calls (QueuedConnection)."""
    app = QApplication.instance()
    for _ in range(20):
        app.processEvents()


# â”€â”€â”€ Events â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestUIEvent:
    def test_default_payload_and_timestamp(self):
        ev = UIEvent("win1", "button_click", "btn1")
        assert ev.payload == {}
        assert ev.timestamp > 0

    def test_positional_args(self):
        ev = UIEvent("win1", "button_click", "btn1", {"x": 1})
        assert ev.window_id == "win1"
        assert ev.widget_id == "btn1"
        assert ev.payload == {"x": 1}


class TestWindowEventQueue:
    def test_put_drain_preserves_order(self):
        q = WindowEventQueue("win1")
        for i in range(3):
            q.put(UIEvent("win1", "button_click", f"b{i}", {"i": i}))
        events = q.drain()
        assert [e.widget_id for e in events] == ["b0", "b1", "b2"]

    def test_drain_empties_queue(self):
        q = WindowEventQueue("win1")
        q.put(UIEvent("win1", "button_click", "b1"))
        q.drain()
        assert q.drain() == []

    def test_drop_oldest_when_full(self):
        q = WindowEventQueue("win1", maxsize=2)
        for i in range(4):
            q.put(UIEvent("win1", "button_click", f"b{i}"))
        events = q.drain()
        assert [e.widget_id for e in events] == ["b2", "b3"]

    def test_seconds_since_activity(self):
        q = WindowEventQueue("win1")
        assert q.seconds_since_activity() >= 0
        q.put(UIEvent("win1", "button_click", "b1"))
        assert q.seconds_since_activity() < 1


# â”€â”€â”€ validate_action â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestValidateAction:
    def test_accepts_tool_action(self):
        assert validate_action({"tool": "get_segments", "params": {}}) is True

    def test_accepts_internal_action(self):
        assert validate_action({"internal": "play_segment"}) is True

    def test_rejects_empty_tool(self):
        assert validate_action({"tool": ""}) is False

    def test_rejects_unknown_internal(self):
        assert validate_action({"internal": "hack_the_planet"}) is False

    def test_rejects_non_dict(self):
        assert validate_action("not a dict") is False
        assert validate_action({"action": "nested"}) is False


# â”€â”€â”€ Factory â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestFactory:
    def test_label_widget(self, qtbot):
        w = create_widget({"type": "label", "id": "l1", "text": "Hola"},
                          on_event=lambda *a: None, window_id="w1")
        assert isinstance(w, QLabel)
        assert w.text() == "Hola"

    def test_button_click_emits_event(self, qtbot):
        events = []
        w = create_widget(
            {"type": "button", "id": "b1", "text": "Go",
             "action": {"tool": "get_segments", "params": {"job_id": "x"}}},
            on_event=lambda t, wid, p: events.append((t, wid, p)),
            window_id="w1",
        )
        assert isinstance(w, QPushButton)
        qtbot.mouseClick(w, Qt.MouseButton.LeftButton)
        assert len(events) == 1
        etype, wid, payload = events[0]
        assert etype == "button_click"
        assert wid == "b1"
        assert payload["action"]["tool"] == "get_segments"

    def test_button_invalid_action_disabled(self, qtbot):
        w = create_widget(
            {"type": "button", "id": "b1", "text": "Bad",
             "action": {"tool": ""}},
            on_event=lambda *a: None, window_id="w1",
        )
        assert isinstance(w, QPushButton)
        assert not w.isEnabled()

    def test_button_flat_tool_fallback_emits_event(self, qtbot):
        events = []
        w = create_widget(
            {"type": "button", "id": "b1", "text": "Go",
             "tool": "get_segments", "params": {"job_id": "x"}},
            on_event=lambda t, wid, p: events.append((t, wid, p)),
            window_id="w1",
        )
        assert isinstance(w, QPushButton)
        assert w.isEnabled()
        qtbot.mouseClick(w, Qt.MouseButton.LeftButton)
        assert len(events) == 1
        etype, wid, payload = events[0]
        assert etype == "button_click"
        assert payload["action"]["tool"] == "get_segments"
        assert payload["action"]["params"] == {"job_id": "x"}

    def test_button_flat_internal_fallback_emits_event(self, qtbot):
        events = []
        w = create_widget(
            {"type": "button", "id": "b1", "text": "Close",
             "internal": "close_window"},
            on_event=lambda t, wid, p: events.append((t, wid, p)),
            window_id="w1",
        )
        assert w.isEnabled()
        qtbot.mouseClick(w, Qt.MouseButton.LeftButton)
        assert events[0][2]["action"]["internal"] == "close_window"

    def test_button_nested_action_wins_over_flat(self, qtbot):
        events = []
        w = create_widget(
            {"type": "button", "id": "b1", "text": "Go",
             "action": {"tool": "get_segments"},
             "tool": "get_queue_status"},
            on_event=lambda t, wid, p: events.append((t, wid, p)),
            window_id="w1",
        )
        qtbot.mouseClick(w, Qt.MouseButton.LeftButton)
        assert events[0][2]["action"]["tool"] == "get_segments"

    def test_button_no_action_disabled(self, qtbot):
        w = create_widget(
            {"type": "button", "id": "b1", "text": "Nada"},
            on_event=lambda *a: None, window_id="w1",
        )
        assert isinstance(w, QPushButton)
        assert not w.isEnabled()

    def test_table_readonly(self, qtbot):
        w = create_widget(
            {"type": "table", "id": "t1", "columns": ["A", "B"],
             "rows": [[1, 2], [3, 4]]},
            on_event=lambda *a: None, window_id="w1",
        )
        assert isinstance(w, QTableWidget)
        assert w.rowCount() == 2
        assert w.columnCount() == 2
        assert not w.item(0, 0).flags() & Qt.ItemFlag.ItemIsEditable

    def test_segment_selector_emits_event(self, qtbot):
        events = []
        w = create_widget(
            {"type": "segment_selector", "id": "s1",
             "segments": [
                 {"start": 0.0, "end": 1.0, "text": "hola"},
                 {"start": 1.0, "end": 2.0, "text": "mundo"},
             ]},
            on_event=lambda t, wid, p: events.append((t, wid, p)),
            window_id="w1",
        )
        assert isinstance(w, QListWidget)
        assert w.count() == 2
        w.setCurrentRow(1)
        assert len(events) == 1
        etype, wid, payload = events[0]
        assert etype == "segment_selected"
        assert wid == "s1"
        assert payload["segment"]["text"] == "mundo"

    def test_audio_player_toggle_emits_event(self, qtbot):
        events = []
        w = create_widget(
            {"type": "audio_player", "id": "a1", "audio_path": "x.wav"},
            on_event=lambda t, wid, p: events.append((t, wid, p)),
            window_id="w1",
        )
        btn = w.findChild(QPushButton)
        assert btn is not None
        qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
        assert len(events) == 1
        assert events[0][0] == "audio_position"
        assert events[0][2]["playing"] is True

    def test_unknown_type_returns_none(self, qtbot):
        w = create_widget({"type": "holo_projector", "id": "x"},
                          on_event=lambda *a: None, window_id="w1")
        assert w is None


# â”€â”€â”€ UIManager â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestNormalizeButtonAction:
    def test_nested_action_passthrough(self):
        d = {"action": {"tool": "get_segments"}}
        assert normalize_button_action(d) == {"tool": "get_segments"}

    def test_flat_tool_fallback(self):
        d = {"tool": "get_segments", "params": {"job_id": "x"}}
        assert normalize_button_action(d) == {
            "tool": "get_segments", "params": {"job_id": "x"},
        }

    def test_flat_internal_fallback(self):
        d = {"internal": "close_window"}
        assert normalize_button_action(d) == {"internal": "close_window"}

    def test_nested_empty_falls_back_to_flat(self):
        d = {"action": {}, "tool": "get_segments"}
        assert normalize_button_action(d) == {"tool": "get_segments"}

    def test_no_action_returns_empty(self):
        assert normalize_button_action({"text": "x"}) == {}

    def test_non_dict_action_ignored(self):
        assert normalize_button_action({"action": "nested"}) == {}


class TestUIManager:
    def test_create_window(self, qtbot):
        mgr = UIManager()
        result = mgr.create_window(
            "Test", "", [{"type": "label", "id": "l1", "text": "Hola"}], {}
        )
        assert result["status"] == "created"
        assert len(result["window_id"]) == 8
        _process_events()
        windows = mgr.list_windows()["windows"]
        assert len(windows) == 1
        assert windows[0]["title"] == "Test"

    def test_list_windows_empty(self, qtbot):
        mgr = UIManager()
        assert mgr.list_windows()["windows"] == []

    def test_get_window_events_empty(self, qtbot):
        mgr = UIManager()
        result = mgr.create_window(
            "Test", "", [{"type": "label", "id": "l1", "text": "Hola"}], {}
        )
        _process_events()
        events = mgr.get_window_events(result["window_id"])
        assert events["window_id"] == result["window_id"]
        assert events["events"] == []

    def test_get_window_events_unknown(self, qtbot):
        mgr = UIManager()
        assert "error" in mgr.get_window_events("nope")

    def test_close_window(self, qtbot):
        mgr = UIManager()
        result = mgr.create_window(
            "Test", "", [{"type": "label", "id": "l1", "text": "Hola"}], {}
        )
        _process_events()
        assert mgr.close_window(result["window_id"])["success"] is True
        assert "error" in mgr.close_window(result["window_id"])

    def test_close_window_unknown(self, qtbot):
        mgr = UIManager()
        assert "error" in mgr.close_window("nope")

    def test_max_windows_limit(self, qtbot):
        mgr = UIManager()
        results = []
        for _ in range(MAX_WINDOWS + 2):
            results.append(mgr.create_window(
                "T", "", [{"type": "label", "id": "l1", "text": "x"}], {}
            ))
        assert all("window_id" in r for r in results[:MAX_WINDOWS])
        assert "error" in results[MAX_WINDOWS]

    def test_update_widget_unknown_window(self, qtbot):
        mgr = UIManager()
        assert "error" in mgr.update_widget("nope", "w", {"text": "x"})

    def test_update_widget_changes_label(self, qtbot):
        mgr = UIManager()
        result = mgr.create_window(
            "Test", "", [{"type": "label", "id": "l1", "text": "Antes"}], {}
        )
        _process_events()
        assert mgr.update_widget(
            result["window_id"], "l1", {"text": "Despues"}
        )["success"] is True
        _process_events()
        win: MUIWindow = mgr._windows[result["window_id"]]
        assert win._widget_map["l1"].text() == "Despues"

    def test_window_closed_event_on_close(self, qtbot):
        mgr = UIManager()
        result = mgr.create_window(
            "Test", "", [{"type": "label", "id": "l1", "text": "Hola"}], {}
        )
        _process_events()
        wid = result["window_id"]
        win: MUIWindow = mgr._windows[wid]
        win.close()
        _process_events()
        events = mgr.get_window_events(wid)
        assert any(e["event_type"] == "window_closed" for e in events["events"])

    def test_window_closed_visible_after_mcp_close(self, qtbot):
        mgr = UIManager()
        result = mgr.create_window(
            "Test", "", [{"type": "label", "id": "l1", "text": "Hola"}], {}
        )
        _process_events()
        wid = result["window_id"]
        assert mgr.close_window(wid)["success"] is True
        _process_events()
        events = mgr.get_window_events(wid)
        assert any(e["event_type"] == "window_closed"
                   for e in events["events"])

    def test_closed_window_events_one_shot(self, qtbot):
        mgr = UIManager()
        result = mgr.create_window(
            "Test", "", [{"type": "label", "id": "l1", "text": "Hola"}], {}
        )
        _process_events()
        wid = result["window_id"]
        assert mgr.close_window(wid)["success"] is True
        _process_events()
        first = mgr.get_window_events(wid)
        assert any(e["event_type"] == "window_closed"
                   for e in first["events"])
        second = mgr.get_window_events(wid)
        assert "error" in second


# â”€â”€â”€ MCP Tools â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestMuiTools:
    @pytest.mark.asyncio
    async def test_create_window_missing_ui_manager(self):
        from madrac.mcp.tools.ui import create_window
        tool = create_window({})
        result = await tool("T", [{"type": "label", "id": "l1"}])
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_window_empty_widgets(self):
        from madrac.mcp.tools.ui import create_window
        tool = create_window({"ui_manager": MagicMock()})
        result = await tool("T", [])
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_window_rejects_non_whitelisted_tool(self):
        from madrac.mcp.tools.ui import create_window
        ui = MagicMock()
        tool = create_window({"ui_manager": ui})
        result = await tool("T", [
            {"type": "button", "id": "b1", "text": "Hack",
             "action": {"tool": "rm_rf"}},
        ])
        assert "error" in result
        ui.create_window.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_window_accepts_whitelisted_tool(self):
        from madrac.mcp.tools.ui import create_window
        ui = MagicMock()
        ui.create_window.return_value = {"window_id": "abc12345",
                                         "status": "created"}
        tool = create_window({"ui_manager": ui})
        result = await tool("T", [
            {"type": "button", "id": "b1", "text": "Segs",
             "action": {"tool": "get_segments", "params": {"job_id": "x"}}},
        ])
        assert result["status"] == "created"
        ui.create_window.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_windows_missing_ui_manager(self):
        from madrac.mcp.tools.ui import list_windows
        tool = list_windows({})
        result = await tool()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_window_events_unknown_window(self):
        from madrac.mcp.tools.ui import get_window_events
        ui = MagicMock()
        ui.get_window_events.return_value = {"error": "Window x not found"}
        tool = get_window_events({"ui_manager": ui})
        result = await tool("x")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_window_button_no_action_returns_example(self):
        from madrac.mcp.tools.ui import create_window
        ui = MagicMock()
        tool = create_window({"ui_manager": ui})
        result = await tool("T", [
            {"type": "button", "id": "b1", "text": "Sin accion"},
        ])
        assert "error" in result
        assert "Expected" in result["error"]
        assert "action" in result["error"]
        ui.create_window.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_window_button_flat_tool_accepted(self):
        from madrac.mcp.tools.ui import create_window
        ui = MagicMock()
        ui.create_window.return_value = {"window_id": "abc12345",
                                         "status": "created"}
        tool = create_window({"ui_manager": ui})
        result = await tool("T", [
            {"type": "button", "id": "b1", "text": "Segs",
             "tool": "get_segments", "params": {"job_id": "x"}},
        ])
        assert result["status"] == "created"

    @pytest.mark.asyncio
    async def test_create_window_button_flat_internal_accepted(self):
        from madrac.mcp.tools.ui import create_window
        ui = MagicMock()
        ui.create_window.return_value = {"window_id": "abc12345",
                                         "status": "created"}
        tool = create_window({"ui_manager": ui})
        result = await tool("T", [
            {"type": "button", "id": "b1", "text": "Cerrar",
             "internal": "close_window"},
        ])
        assert result["status"] == "created"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mui_tool", [
        "create_window", "update_widget", "close_window",
        "list_windows", "get_window_events",
    ])
    async def test_create_window_button_allows_mui_tools(self, mui_tool):
        from madrac.mcp.tools.ui import create_window
        ui = MagicMock()
        ui.create_window.return_value = {"window_id": "abc12345",
                                         "status": "created"}
        tool = create_window({"ui_manager": ui})
        result = await tool("T", [
            {"type": "button", "id": "b1", "text": mui_tool,
             "action": {"tool": mui_tool}},
        ])
        assert result["status"] == "created", mui_tool
