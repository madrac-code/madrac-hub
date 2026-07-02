"""MADRAC-DUBBING v3 - Dubbing Extension"""
try:
    from madrac import __version__ as __version__
except ImportError:
    __version__ = "3.0.0"
__author__ = "MADRAC Team"

from .pipeline.models import DubbingJob, DubbingConfig, DubbingStatus

__all__ = ["DubbingJob", "DubbingConfig", "DubbingStatus", "__version__"]
