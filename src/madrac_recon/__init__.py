"""RECON — MADRAC speaker recognition and diarization.

Phase 1: speaker diarization persisted into SharedWorkspace
(stems/speakers/speaker_N.wav + speakers.json + metadata).
Phase 2: speaker-to-subtitle segment mapping (speaker_segments.json).
"""

from .diarize import diarize_job, diarize_video
from .models import DiarizationResult, SpeakerSegment
from .map_segments import map_job, map_speakers_to_segments, MappingResult, MappedSegment

__all__ = [
    "diarize_job",
    "diarize_video",
    "map_job",
    "map_speakers_to_segments",
    "MappingResult",
    "MappedSegment",
    "DiarizationResult",
    "SpeakerSegment",
]