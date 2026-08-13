"""RECON — MADRAC speaker recognition and diarization.

Phase 1: speaker diarization persisted into SharedWorkspace
(stems/speakers/speaker_N.wav + speakers.json + metadata).
"""

from .diarize import diarize_job, diarize_video
from .models import DiarizationResult, SpeakerSegment

__all__ = ["diarize_job", "diarize_video", "DiarizationResult", "SpeakerSegment"]