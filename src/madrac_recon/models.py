"""RECON data contracts (Phase 1 — diarization)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpeakerSegment:
    """A contiguous turn of one speaker, in seconds of source audio."""

    start: float
    end: float


@dataclass
class DiarizationResult:
    """Result of a diarization run, ready to be persisted."""

    job_id: str
    speaker_count: int
    speakers: list[dict[str, Any]] = field(default_factory=list)
    speaker_paths: list[str] = field(default_factory=list)
    diarizer: str = "resemblyzer"
    sample_rate: int = 16000
    source_audio: str = ""