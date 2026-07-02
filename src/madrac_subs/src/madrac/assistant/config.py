import json
import os
import sys
from pathlib import Path


def _assistant_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "madrac_asistente"


def _writable_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return _assistant_root()


def load_config() -> dict:
    path = _writable_dir() / "config.json"
    if not path.exists():
        path = _assistant_root() / "config.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(cfg: dict):
    path = _writable_dir() / "config.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def load_profile() -> dict:
    path = _writable_dir() / "perfiles" / "default.json"
    if not path.exists():
        path = _assistant_root() / "perfiles" / "default.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}
