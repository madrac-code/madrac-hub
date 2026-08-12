"""MUI window tools for MADRAC MCP — create and manage procedural windows.

Security:
- Buttons may only trigger tools in a fixed whitelist
  (15 core MADRAC tools + 3 internal actions).
- Max MAX_WINDOWS windows per session (enforced by UIManager).
- Idle windows are auto-closed after 10 minutes (enforced by UIManager).
"""
from typing import Any

# Whitelist: the 15 original MCP tools that buttons may invoke.
_BUTTON_TOOL_WHITELIST = frozenset({
    "get_queue_status",
    "pause_processing",
    "resume_processing",
    "transcribe_file",
    "translate_subtitles",
    "execute_assistant_action",
    "read_config",
    "get_dubbing_status",
    "start_dubbing",
    "get_workspace_info",
    "list_workspaces",
    "get_segments",
    "rename_speaker",
    "edit_subtitle_segment",
    "export_srt",
})

# Internal actions handled locally by UIManager.
_INTERNAL_ACTIONS = frozenset({
    "play_segment",
    "record_segment",
    "close_window",
})


def create_window(app_state: dict[str, Any]):
    async def _create_window(
        title: str,
        widgets: list[dict],
        job_id: str = "",
        keybindings: dict | None = None,
    ) -> dict:
        """
        Create a new MUI window with procedural widgets.

        Args:
            title: Window title
            widgets: List of widget descriptors
                      [{type, id, ...}, ...]
                     Supported types: label, button, table,
                      segment_selector, audio_player, waveform
            job_id: Optional workspace job ID (for ui_state.json
                    persistence and audio playback)
            keybindings: Optional dict of key -> action (reserved)

        Returns:
            {"window_id": "...", "status": "created"}
            or {"error": "..."}
        """
        ui = app_state.get("ui_manager")
        if ui is None:
            return {"error": "UIManager not available"}

        if not isinstance(widgets, list) or not widgets:
            return {"error": "widgets must be a non-empty list"}

        for w in widgets:
            if not isinstance(w, dict) or w.get("type") != "button":
                continue
            action = w.get("action", {})
            if not isinstance(action, dict):
                return {"error": "Button action must be an object"}
            if "tool" in action:
                if action["tool"] not in _BUTTON_TOOL_WHITELIST:
                    return {
                        "error": f"Tool '{action['tool']}' is not in the "
                                 "button action whitelist"
                    }
            elif "internal" in action:
                if action["internal"] not in _INTERNAL_ACTIONS:
                    return {
                        "error": f"Internal action "
                                 f"'{action['internal']}' is not allowed"
                    }
            else:
                return {"error": "Button action needs 'tool' or 'internal'"}

        return ui.create_window(
            title, job_id, widgets, keybindings or {}
        )
    return _create_window


def update_widget(app_state: dict[str, Any]):
    async def _update_widget(
        window_id: str,
        widget_id: str,
        props: dict,
    ) -> dict:
        """
        Update widget properties in a live MUI window.

        Args:
            window_id: Window ID from create_window
            widget_id: Widget ID from the window's descriptors
            props: Supported props: {"text": "...", "enabled": bool}

        Returns:
            {"success": True} or {"error": "..."}
        """
        ui = app_state.get("ui_manager")
        if ui is None:
            return {"error": "UIManager not available"}
        return ui.update_widget(window_id, widget_id, props)
    return _update_widget


def close_window(app_state: dict[str, Any]):
    async def _close_window(window_id: str) -> dict:
        """
        Close an MUI window by ID.

        Args:
            window_id: Window ID from create_window

        Returns:
            {"success": True, "window_id": "..."} or {"error": "..."}
        """
        ui = app_state.get("ui_manager")
        if ui is None:
            return {"error": "UIManager not available"}
        return ui.close_window(window_id)
    return _close_window


def list_windows(app_state: dict[str, Any]):
    async def _list_windows() -> dict:
        """
        List open MUI windows with their status.

        Returns:
            {"windows": [{"window_id": "...", "title": "...",
                          "job_id": "...", "visible": bool,
                          "inactive_seconds": float}, ...]}
            or {"error": "..."}
        """
        ui = app_state.get("ui_manager")
        if ui is None:
            return {"error": "UIManager not available"}
        return ui.list_windows()
    return _list_windows


def get_window_events(app_state: dict[str, Any]):
    async def _get_window_events(window_id: str) -> dict:
        """
        Get pending user-interaction events for an MUI window.
        Reading drains the queue (events are consumed).

        Args:
            window_id: Window ID from create_window

        Returns:
            {"window_id": "...", "events": [
                {"event_type": "...", "widget_id": "...",
                 "payload": {...}, "timestamp": float},
                ...
            ]} or {"error": "..."}
        """
        ui = app_state.get("ui_manager")
        if ui is None:
            return {"error": "UIManager not available"}
        return ui.get_window_events(window_id)
    return _get_window_events


__all__ = [
    "create_window",
    "update_widget",
    "close_window",
    "list_windows",
    "get_window_events",
]