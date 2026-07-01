"""Thread configuration for Whisper, CTranslate2, and PyTorch.

Detects CPU cores, avoids oversubscription, and configures native thread pools.
"""

import logging
import os
import platform
from typing import Optional

logger = logging.getLogger("madrac.threading")


_DEFAULTS = {
    "whisper_threads": 0,
    "torch_threads": 0,
    "ctranslate2_intra_threads": 0,
    "ctranslate2_inter_threads": 1,
}


def _detect_physical_cores() -> int:
    """Detect physical CPU cores. Falls back to logical count."""
    try:
        import psutil
        phys = psutil.cpu_count(logical=False)
        if phys and phys > 0:
            return phys
        log = psutil.cpu_count(logical=True)
        return log or 4
    except (ImportError, Exception):
        pass
    import os
    return os.cpu_count() or 4


def _detect_logical_cores() -> int:
    """Detect logical CPU cores."""
    try:
        import psutil
        return psutil.cpu_count(logical=True) or 4
    except (ImportError, Exception):
        pass
    import os
    return os.cpu_count() or 4


def _has_gpu_nvidia() -> bool:
    """Check if an NVIDIA GPU is available via PyTorch."""
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


def _has_gpu_apple() -> bool:
    """Check if Apple Metal is available."""
    if platform.system() != "Darwin":
        return False
    try:
        import torch
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return True
    except Exception:
        pass
    return False


def detect_gpu() -> Optional[str]:
    """Detect available GPU. Returns 'cuda', 'mps', or None."""
    if _has_gpu_nvidia():
        return "cuda"
    if _has_gpu_apple():
        return "mps"
    return None


def configure_threading(
    user_thread_count: int = 0,
    *,
    force_whisper: Optional[int] = None,
    force_torch: Optional[int] = None,
    force_ctranslate2: Optional[int] = None,
) -> int:
    """Configure threading for all ML frameworks.

    Args:
        user_thread_count: User preference (0 = auto-detect physical cores).
        force_whisper: Override faster-whisper cpu_threads.
        force_torch: Override torch.set_num_threads().
        force_cranslate2: Override CTranslate2 intra_threads.

    Returns:
        The chosen thread count.
    """
    phys_cores = _detect_physical_cores()
    log_cores = _detect_logical_cores()
    # Use physical cores by default, but at most logical - 1 for UI/OS
    auto_n = max(1, min(phys_cores, log_cores - 1) if log_cores > 2 else phys_cores)
    n = user_thread_count if user_thread_count > 0 else auto_n

    whisper_threads = force_whisper if force_whisper is not None else n
    torch_threads = force_torch if force_torch is not None else n
    ctranslate2_threads = force_ctranslate2 if force_ctranslate2 is not None else n

    # --- PyTorch ---
    try:
        import torch
        current = torch.get_num_threads()
        if torch_threads != current:
            torch.set_num_threads(torch_threads)
            logger.info("torch.set_num_threads(%d) (was %d)", torch_threads, current)
        else:
            logger.debug("torch threads already %d", current)
    except Exception as e:
        logger.warning("Could not configure torch threads: %s", e)

    # --- CTranslate2 ---
    try:
        import ctranslate2
        env_key = "CT2_CUDA_CACHED_CAPACITY"
        if os.environ.get(env_key) is None:
            os.environ[env_key] = str(ctranslate2_threads * 256)
        logger.info("CTranslate2 configured: intra_threads=%d", ctranslate2_threads)
    except ImportError:
        logger.debug("CTranslate2 not installed, skipping thread config")

    logger.info(
        "Thread config: phys=%d log=%d chosen=%d whisper=%d torch=%d ct2=%d",
        phys_cores, log_cores, n,
        whisper_threads, torch_threads, ctranslate2_threads,
    )

    return n


def get_thread_info() -> dict:
    """Return current thread configuration as a dict (for profiling)."""
    info = {**_DEFAULTS}
    try:
        import torch
        info["torch_threads"] = torch.get_num_threads()
    except Exception:
        pass
    info["whisper_threads"] = info["torch_threads"]
    info["ctranslate2_intra_threads"] = info["torch_threads"]
    info["phys_cores"] = _detect_physical_cores()
    info["log_cores"] = _detect_logical_cores()
    info["gpu"] = detect_gpu()
    info["platform"] = platform.system()
    return info
