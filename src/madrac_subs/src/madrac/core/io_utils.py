"""Unified UTF-8 file I/O — single import, guaranteed encoding, no surprises."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

_ENCODING = "utf-8"

PathLike = Union[str, Path]


def read_text(path: PathLike) -> str:
    return Path(path).read_text(encoding=_ENCODING)


def write_text(path: PathLike, content: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding=_ENCODING)


def read_lines(path: PathLike) -> List[str]:
    return read_text(path).splitlines()


def read_binary(path: PathLike) -> bytes:
    return Path(path).read_bytes()


def write_binary(path: PathLike, data: bytes) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def read_json(path: PathLike) -> Any:
    return json.loads(read_text(path))


def write_json(path: PathLike, data: Any, **kwargs) -> None:
    kwargs.setdefault("ensure_ascii", False)
    kwargs.setdefault("indent", 2)
    write_text(path, json.dumps(data, **kwargs))


def ensure_utf8(path: PathLike) -> bool:
    """Re-read file and rewrite as UTF-8 if not already. Returns True if changed."""
    p = Path(path)
    original = p.read_bytes()
    try:
        decoded = original.decode("utf-8")
        return False
    except UnicodeDecodeError:
        for enc in ("utf-8-sig", "utf-16", "latin-1"):
            try:
                decoded = original.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            return False
        write_text(p, decoded)
        return True
