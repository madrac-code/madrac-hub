"""Model management for Whisper and MarianMT.

Detection, download, and removal of AI models via HuggingFace Hub.
Port of v2 model_manager.py with v3 logging and config.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from ..core import get_logger

logger = get_logger("models")

_TAMANOS_ESTIMADOS: Dict[str, int] = {
    "tiny":   75 * 1024 * 1024,
    "base":   150 * 1024 * 1024,
    "small":  500 * 1024 * 1024,
    "medium": 1500 * 1024 * 1024,
    "es":     300 * 1024 * 1024,
    "fr":     310 * 1024 * 1024,
    "it":     300 * 1024 * 1024,
    "de":     320 * 1024 * 1024,
    "pt":     300 * 1024 * 1024,
}

MODELOS_WHISPER = ("tiny", "base", "small", "medium")
MODELOS_MARIAN_DISPONIBLES = ("es", "fr", "it", "de", "pt")
REPO_WHISPER = "Systran/faster-whisper-{}"
REPO_MARIAN = "Helsinki-NLP/opus-mt-en-{}"


def _ruta_cache_hub() -> Path:
    return Path.home() / ".cache" / "huggingface" / "hub"


def _normalizar_repo_id(repo_id: str) -> str:
    return repo_id.replace("/", "--")


def _ruta_modelo_en_cache(repo_id: str) -> Path:
    return _ruta_cache_hub() / f"models--{_normalizar_repo_id(repo_id)}"


def formatear_tamano(bytes_: int) -> str:
    if bytes_ >= 1_073_741_824:
        return f"{bytes_ / 1_073_741_824:.1f} GB"
    if bytes_ >= 1_048_576:
        return f"{bytes_ / 1_048_576:.0f} MB"
    if bytes_ >= 1024:
        return f"{bytes_ / 1024:.0f} KB"
    return f"{bytes_} B"


def tamano_estimado(modelo: str) -> int:
    return _TAMANOS_ESTIMADOS.get(modelo, 300 * 1024 * 1024)


def detectar_modelos_instalados() -> Dict[str, List[str]]:
    """Scan ~/.cache/huggingface/hub/ and return found models.

    Returns:
        {'whisper': [...], 'marian': [...], 'otros': [...]}
    """
    resultado: Dict[str, List[str]] = {"whisper": [], "marian": [], "otros": []}
    hub = _ruta_cache_hub()
    if not hub.exists():
        return resultado

    for entrada in hub.iterdir():
        if not entrada.is_dir() or not entrada.name.startswith("models--"):
            continue
        nombre = entrada.name
        if "faster-whisper" in nombre:
            for t in MODELOS_WHISPER:
                if f"faster-whisper-{t}" in nombre:
                    resultado["whisper"].append(t)
                    break
            else:
                resultado["otros"].append(nombre)
        elif "opus-mt" in nombre:
            for l in MODELOS_MARIAN_DISPONIBLES:
                if f"opus-mt-en-{l}" in nombre:
                    resultado["marian"].append(l)
                    break
            else:
                resultado["otros"].append(nombre)
        else:
            resultado["otros"].append(nombre)

    return resultado


def hay_modelos_whisper() -> bool:
    return len(detectar_modelos_instalados().get("whisper", [])) > 0


def hay_modelos_marian(idioma: Optional[str] = None) -> bool:
    instalados = detectar_modelos_instalados().get("marian", [])
    if idioma:
        return idioma in instalados
    return len(instalados) > 0


def descargar_modelo_whisper(tamano: str, callback: Optional[Callable[[str], None]] = None) -> bool:
    repo_id = REPO_WHISPER.format(tamano)
    return _descargar_snapshot(repo_id, callback)


def descargar_modelo_marian(idioma: str, callback: Optional[Callable[[str], None]] = None) -> bool:
    repo_id = REPO_MARIAN.format(idioma)
    return _descargar_snapshot(repo_id, callback)


def _snapshot_valido(repo_id: str) -> bool:
    """Verify a model has at least one complete snapshot."""
    modelo_path = _ruta_modelo_en_cache(repo_id)
    if not modelo_path.exists():
        return False
    snapshots = modelo_path / "snapshots"
    if not snapshots.exists():
        return False
    for s in snapshots.iterdir():
        if s.is_dir() and any(s.rglob("*")):
            return True
    return False


def _descargar_snapshot(repo_id: str, callback: Optional[Callable[[str], None]] = None) -> bool:
    """Download model from HuggingFace Hub with cache check and retries."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        if callback:
            callback("ERROR: huggingface_hub not installed")
        return False

    if _snapshot_valido(repo_id):
        if callback:
            callback(f"[OK] {repo_id} already cached")
        return True

    for intento in range(3):
        try:
            if callback:
                if intento > 0:
                    callback(f"Retrying {repo_id} (attempt {intento + 1}/3)...")
                else:
                    callback(f"Downloading {repo_id}...")
            snapshot_download(
                repo_id=repo_id,
                local_files_only=False,
                resume_download=True,
                ignore_patterns=["*.h5", "*.ot"],
            )
            if callback:
                callback(f"[OK] {repo_id} downloaded")
            return True
        except Exception as e:
            if callback:
                callback(f"[ERR] Attempt {intento + 1}/3: {e}")
            if intento < 2:
                espera = 2 ** (intento + 1)
                if callback:
                    callback(f"[WAIT] Waiting {espera}s before retry...")
                time.sleep(espera)

    return False


def eliminar_modelo(repo_id_o_tamano: str) -> int:
    """Delete a model from cache. Accepts 'base', 'es', or full repo_id.

    Returns bytes freed.
    """
    if "/" not in repo_id_o_tamano:
        if repo_id_o_tamano in MODELOS_WHISPER:
            repo_id = REPO_WHISPER.format(repo_id_o_tamano)
        elif repo_id_o_tamano in MODELOS_MARIAN_DISPONIBLES:
            repo_id = REPO_MARIAN.format(repo_id_o_tamano)
        else:
            return 0
    else:
        repo_id = repo_id_o_tamano

    ruta = _ruta_modelo_en_cache(repo_id)
    if not ruta.exists():
        return 0

    tamano = sum(f.stat().st_size for f in ruta.rglob("*") if f.is_file())
    try:
        shutil.rmtree(ruta)
        return tamano
    except OSError:
        return 0


def limpiar_modelos_no_seleccionados(whisper_actual: str, marian_actual: str) -> int:
    """Delete models not matching current selection.

    Returns total bytes freed.
    """
    total = 0
    instalados = detectar_modelos_instalados()

    for t in instalados.get("whisper", []):
        if t != whisper_actual and t in MODELOS_WHISPER:
            total += eliminar_modelo(t)

    for l in instalados.get("marian", []):
        if l != marian_actual and l in MODELOS_MARIAN_DISPONIBLES:
            total += eliminar_modelo(l)

    return total


def primer_inicio_pendiente() -> bool:
    """True if no Whisper model has valid snapshots."""
    instalados = detectar_modelos_instalados().get("whisper", [])
    if not instalados:
        return True
    for t in instalados:
        repo_id = REPO_WHISPER.format(t)
        if _snapshot_valido(repo_id):
            return False
    return True
