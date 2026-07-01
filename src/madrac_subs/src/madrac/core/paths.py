"""
Path resolution for MADRAC-SUBS v3.
Handles both development and frozen (PyInstaller) environments.
"""

import sys
from pathlib import Path
from typing import Optional


def is_frozen() -> bool:
    """Check if running in a PyInstaller frozen environment."""
    return getattr(sys, "frozen", False)


def get_base_path() -> Path:
    """
    Get the base path for the application.
    
    In frozen mode: returns sys._MEIPASS (PyInstaller extraction dir)
    In dev mode: returns the project root (parent of src/)
    """
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # Dev mode: go up from src/madrac/core/paths.py to project root
    return Path(__file__).parent.parent.parent.parent


def get_project_root() -> Path:
    """
    Get the project root directory.
    
    In frozen mode: returns the directory containing the executable
    In dev mode: returns the project root
    """
    if is_frozen():
        return Path(sys.executable).parent
    return get_base_path()


def get_resource_path(relative: str) -> Path:
    """
    Resolve a path to a resource (UI files, icons, bundled config, etc.).
    
    Searches in order:
    1. sys._MEIPASS (frozen bundle)
    2. Project root / resources
    3. Relative to current file (dev fallback)
    """
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
        candidates = [base, base / "resources", base / "_internal" / "resources"]
        for c in candidates:
            p = c / relative
            if p.exists():
                return p
        return base / relative
    
    # Dev mode
    project_root = get_project_root()
    candidates = [
        project_root / "resources" / relative,
        project_root / "src" / "madrac" / "resources" / relative,
        Path(__file__).parent.parent.parent / "resources" / relative,
    ]
    for c in candidates:
        if c.exists():
            return c
    return project_root / "resources" / relative


def get_ui_path(name: str) -> Path:
    """Get path to a .ui file."""
    return get_resource_path(f"ui/{name}")


def get_config_path() -> Path:
    """
    Get the path to the bundled default config.json.
    This is READ-ONLY - user config goes to get_user_config_path().
    """
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
        for c in [base, base.parent, base / "_internal"]:
            p = c / "config.json"
            if p.exists():
                return p
    return get_project_root() / "config.json"


def get_cache_dir() -> Path:
    """Alias for get_user_config_dir — cache directory."""
    return get_user_config_dir()

def get_user_config_dir() -> Path:
    """Get the user config directory (~/.cache/madrac-subs)."""
    return Path.home() / ".cache" / "madrac-subs"


def get_user_config_path() -> Path:
    """Get the path to the user's persistent config.json."""
    return get_user_config_dir() / "config.json"


def get_user_data_dir() -> Path:
    """Get the user data directory for logs, queue, etc."""
    return get_user_config_dir()


def get_log_path() -> Path:
    """Get the path to the log file."""
    return get_user_data_dir() / "madrac-subs.log"


def get_queue_path() -> Path:
    """Get the path to the persistent queue file."""
    return get_user_data_dir() / "queue.json"


def get_session_path() -> Path:
    """Get the path to the Supabase session file."""
    return get_user_data_dir() / "session.json"


def get_temp_dir() -> Path:
    """Get the temporary files directory."""
    if is_frozen():
        # In frozen mode, use a temp dir next to executable or system temp
        return Path(sys.executable).parent / ".cache" / "temporal"
    return get_project_root() / ".cache" / "temporal"


def get_plugins_dir() -> Path:
    """Get the plugins directory."""
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
        for c in [base, base.parent, base / "_internal"]:
            p = c / "plugins"
            if p.exists():
                return p
    return get_project_root() / "plugins"


def ensure_dirs() -> None:
    """Ensure all required user directories exist."""
    get_user_config_dir().mkdir(parents=True, exist_ok=True)
    get_temp_dir().mkdir(parents=True, exist_ok=True)
    get_plugins_dir().mkdir(parents=True, exist_ok=True)