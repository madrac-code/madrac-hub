"""File hashing utilities."""

import hashlib
from pathlib import Path
from typing import Optional

from ..core.logging import get_logger

logger = get_logger("utils.hashing")


def sha256(file_path: Path, block_size: int = 65536) -> Optional[str]:
    """Compute SHA-256 of a file in streaming fashion."""
    try:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                block = f.read(block_size)
                if not block:
                    break
                h.update(block)
        return h.hexdigest()
    except Exception as e:
        logger.warning("SHA256 error for %s: %s", file_path, e)
        return None
