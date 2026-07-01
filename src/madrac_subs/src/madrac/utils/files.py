"""File validation, path normalization, and cleanup utilities."""

import os
from pathlib import Path
from typing import Optional, Tuple

from ..core.logging import get_logger

logger = get_logger("utils.files")


def validate_file(path: str) -> Tuple[bool, str]:
    """Validate that a file exists and is a supported media format."""
    p = Path(path)
    if not p.exists():
        return False, "File does not exist"
    if not p.is_file():
        return False, "Not a file"
    # Quick extension check (exhaustive list in audio stage)
    ext = p.suffix.lower()
    supported = {
        ".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v", ".wmv",
        ".3gp", ".3g2", ".mts", ".ts", ".vob",
        ".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma", ".opus",
    }
    if ext not in supported:
        return False, f"Unsupported format: {ext}"
    if p.stat().st_size < 100:
        return False, "File too small (possible corruption)"
    if not os.access(p, os.R_OK):
        return False, "No read permission"
    return True, ""


def normalize_path(path: str) -> str:
    """Resolve path to absolute, normalised form."""
    return str(Path(path).resolve())


def output_dir_for(file_path: str, suffix: str = "_subtitles") -> str:
    """Create output directory next to source file."""
    p = Path(file_path)
    out = p.parent / f"{p.stem}{suffix}"
    out.mkdir(parents=True, exist_ok=True)
    return str(out)


def remove_temp(path: str) -> None:
    """Remove a temp file silently."""
    try:
        p = Path(path)
        if p.exists():
            p.unlink()
    except Exception as e:
        logger.debug("Could not remove %s: %s", path, e)


def get_file_stem(path: str) -> str:
    """Get file name without extension."""
    return Path(path).stem
