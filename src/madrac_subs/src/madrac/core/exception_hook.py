"""Global exception hooks for sys.excepthook, threading, and Qt."""

import sys
import traceback
import threading
from pathlib import Path

_logger = None


def _log() -> any:
    global _logger
    if _logger is None:
        from ..core.logging import get_logger
        _logger = get_logger("core.exception_hook")
    return _logger


_original_excepthook = sys.excepthook
_original_threading_excepthook = threading.excepthook


def _format_exception(exc_type, exc_value, exc_tb) -> str:
    lines = [
        "=" * 60,
        "MADRAC-SUBS ERROR (no recuperable)",
        "=" * 60,
    ]
    lines.extend(traceback.format_exception(exc_type, exc_value, exc_tb))
    lines.append("=" * 60)
    return "\n".join(lines)


def _show_qt_dialog(summary: str, details: str) -> None:
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            return
        from ..ui.dialogs.crash_dialog import CrashDialog
        dlg = CrashDialog(summary, details)
        dlg.exec()
    except Exception:
        pass


def _handle_exception(exc_type, exc_value, exc_tb) -> None:
    details = _format_exception(exc_type, exc_value, exc_tb)
    _log().critical(details)
    print(details, file=sys.stderr, flush=True)
    summary = f"{exc_type.__name__}: {exc_value}"
    _show_qt_dialog(summary, details)


def _sys_hook(exc_type, exc_value, exc_tb) -> None:
    if exc_type is KeyboardInterrupt:
        _original_excepthook(exc_type, exc_value, exc_tb)
        return
    _handle_exception(exc_type, exc_value, exc_tb)


def _threading_hook(args: threading.ExceptHookArgs) -> None:
    _handle_exception(args.exc_type, args.exc_value, args.exc_traceback)


def _qt_message_handler(mode, context, message) -> None:
    if mode >= 4:
        _log().error("Qt %s: %s", mode, message)


def install_exception_hooks() -> None:
    sys.excepthook = _sys_hook
    threading.excepthook = _threading_hook
    try:
        from PySide6.QtCore import qInstallMessageHandler
        qInstallMessageHandler(_qt_message_handler)
    except ImportError:
        pass


def uninstall_exception_hooks() -> None:
    sys.excepthook = _original_excepthook
    threading.excepthook = _original_threading_excepthook
    try:
        from PySide6.QtCore import qInstallMessageHandler
        qInstallMessageHandler(None)
    except ImportError:
        pass
