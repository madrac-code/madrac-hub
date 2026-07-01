"""
Core infrastructure for MADRAC-SUBS v3.
"""

from .paths import (
    is_frozen,
    get_base_path,
    get_project_root,
    get_resource_path,
    get_ui_path,
    get_config_path,
    get_user_config_dir,
    get_user_config_path,
    get_user_data_dir,
    get_log_path,
    get_queue_path,
    get_session_path,
    get_temp_dir,
    get_plugins_dir,
    ensure_dirs,
)
from .logging import (
    setup_logging,
    get_logger,
    set_qt_message_handler,
    log_startup_info,
)
from .events import get_bus, EventBus
from .threading import (
    configure_threading,
    detect_gpu,
    get_thread_info,
)
from .exception_hook import (
    install_exception_hooks,
    uninstall_exception_hooks,
)
from .io_utils import (
    read_text, write_text, read_lines,
    read_binary, write_binary,
    read_json, write_json, ensure_utf8,
)
from .parser import parse_video_filename


__all__ = [
    # paths
    "is_frozen",
    "get_base_path",
    "get_project_root",
    "get_resource_path",
    "get_ui_path",
    "get_config_path",
    "get_user_config_dir",
    "get_user_config_path",
    "get_user_data_dir",
    "get_log_path",
    "get_queue_path",
    "get_session_path",
    "get_temp_dir",
    "get_plugins_dir",
    "ensure_dirs",
    # logging
    "setup_logging",
    "get_logger",
    "set_qt_message_handler",
    "log_startup_info",
    # events
    "get_bus",
    "EventBus",
    # threading
    "configure_threading",
    "detect_gpu",
    "get_thread_info",
    # exception hooks
    "install_exception_hooks",
    "uninstall_exception_hooks",
    # io_utils
    "read_text",
    "write_text",
    "read_lines",
    "read_binary",
    "write_binary",
    "read_json",
    "write_json",
    "ensure_utf8",
]
