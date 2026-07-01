"""System-level utilities: open explorer, disk space, cleanup."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict

from ..core.logging import get_logger
from ..core import write_text

logger = get_logger("utils.system")


def open_in_explorer(path: Path) -> None:
    """Open folder in system file manager."""
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def _dir_size(path: Path) -> int:
    """Recursively sum file sizes in a directory."""
    if not path.exists():
        return 0
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total


def disk_usage_by_category() -> Dict[str, int]:
    """Calculate disk usage per cache category in bytes."""
    result: Dict[str, int] = {
        "whisper": 0, "marian": 0, "cache_hf": 0, "logs": 0, "temp": 0,
    }
    hf_path = Path.home() / ".cache" / "huggingface" / "hub"
    if hf_path.exists():
        for d in hf_path.iterdir():
            if not d.is_dir():
                continue
            sz = _dir_size(d)
            name = d.name.lower()
            if "faster-whisper" in name:
                result["whisper"] += sz
            elif "opus-mt" in name:
                result["marian"] += sz
            else:
                result["cache_hf"] += sz
    log_path = Path.home() / ".cache" / "madrac-subs" / "madrac-subs.log"
    if log_path.exists():
        try:
            result["logs"] = log_path.stat().st_size
        except OSError:
            pass
    return result


def clean_temp() -> int:
    """Remove temp files, return bytes freed."""
    from ..core.paths import get_temp_dir
    temp = get_temp_dir()
    if not temp.exists():
        return 0
    sz = _dir_size(temp)
    for f in temp.rglob("*"):
        if f.is_file():
            try:
                f.unlink()
            except OSError:
                pass
    return sz


def clean_logs() -> int:
    """Truncate log file, return bytes freed."""
    log_path = Path.home() / ".cache" / "madrac-subs" / "madrac-subs.log"
    if not log_path.exists():
        return 0
    try:
        sz = log_path.stat().st_size
        write_text(log_path, "")
        return sz
    except OSError as e:
        logger.warning("Error truncating log: %s", e)
        return 0


def clean_hf_cache() -> int:
    """Remove HuggingFace cache entirely, return bytes freed."""
    import shutil
    hf = Path.home() / ".cache" / "huggingface" / "hub"
    if not hf.exists():
        return 0
    sz = _dir_size(hf)
    try:
        shutil.rmtree(hf)
    except OSError as e:
        logger.warning("Error cleaning HF cache: %s", e)
    return sz


def clean_all() -> int:
    """Run all cleanups, return total bytes freed."""
    total = 0
    total += clean_temp()
    total += clean_logs()
    total += clean_hf_cache()
    return total
