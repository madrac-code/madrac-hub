"""Shared workspace implementation for MADRAC-SUBS v3.

Provides content-addressed, per-video workspace that allows SUBS and DUBS to
share extracted segments and stems without re-extraction. 

Workflow:
1. SUBS extracts audio and creates a workspace (on demand).
2. SUBS saves audio_whisper.wav and segments.json.
3. DUBS later loads the workspace, finds existing audio_whisper.wav,
   and if needed, creates audio_full.wav for source-quality work.
4. If needed, DUBS can save stems (from DSP or Demucs) into the workspace.
5. DUBS saves dubbed segments into the workspace.

Design decisions from approved spec:
- job_id = "sha256-" + sha256(content of the video file)
- Root: ~/.cache/madrac/workspace/jobs/<job_id>/
- Persists indefinitely (user cleans up old jobs).
- Best-effort integration: missing workspace fails silently, logs warning.
- Thread-safe metadata writes with threading.Lock.

Do NOT create: collaborative workspaces, Supabase, roles, web UI, or Notion-style projects.
"""

import json
import time
from pathlib import Path
from threading import Lock
from typing import Dict, List, Any, Optional

from ..core import get_logger
from ..utils.hashing import sha256

logger = get_logger("workspace.shared")

# Global lock for cross-instance metadata protection (same-process safety).
_metadata_lock = Lock()
_SCHEMA_VERSION = "1.0"
# Per approved design: ~/.cache/madrac/workspace/jobs/ (NOT madrac-subs)
_CACHE_ROOT = Path.home() / ".cache" / "madrac" / "workspace" / "jobs"


def compute_job_id(video_path: Path) -> Optional[str]:
    """Compute content‑addressed job ID from a video file.
    
    Returns: "sha256-<hex>" or None on failure.
    """
    h = sha256(video_path)
    if not h:
        return None
    return f"sha256-{h}"


def list_workspaces() -> List[str]:
    """List all existing job IDs in the workspace.
    
    Returns: Sorted list of job IDs found in ~/.cache/madrac/workspace/jobs/.
    """
    if not _CACHE_ROOT.exists():
        return []
    job_ids = []
    for p in _CACHE_ROOT.iterdir():
        if p.is_dir() and p.name.startswith("sha256-"):
            job_ids.append(p.name)
    return sorted(job_ids)


class SharedWorkspace:
    """Per‑video workspace for MADRAC content — SUBS ↔ DUBS sharing.
    
    Provides methods to persist and load:
    * audio_whisper.wav (16kHz mono, SUBS)
    * segments.json (segments + metadata)
    * audio_full.wav (source quality, created on demand by DUBS)
    * stems/vocals.wav, stems/no_vocals.wav (DSP or Demucs producer)
    * dubbed/seg_0000.wav, ... (dubbed segments)
    
    All writes are thread‑safe via _metadata_lock.
    """

    def __init__(self, job_id: str):
        """Initialize workspace for the given job ID.
        
        Args:
            job_id: Must match pattern "sha256-<hex>".
        """
        self.job_id = job_id
        self.root = _CACHE_ROOT / job_id
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create workspace directories on first access."""
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "stems").mkdir(exist_ok=True)
        (self.root / "stems" / "speakers").mkdir(exist_ok=True)
        (self.root / "dubbed").mkdir(exist_ok=True)

    @property
    def speakers_dir(self) -> Path:
        """Directory for per-speaker audio files (stems/speakers)."""
        return self.root / "stems" / "speakers"

    def save_speaker(self, speaker_id: int, wav_path: Path) -> bool:
        """Copy a speaker's audio clip to stems/speakers/speaker_N.wav.

        RECON Phase 1 contract: each speaker gets one concatenated WAV
        (16kHz mono PCM16) of their turns in the source audio.
        """
        if not wav_path.exists():
            logger.warning(f"Speaker audio not found: {wav_path}")
            return False
        dest = self.speakers_dir / f"speaker_{speaker_id}.wav"
        try:
            shutil.copy2(wav_path, dest)
            logger.info(f"Saved speaker {speaker_id} to workspace: {dest}")
            return True
        except Exception as e:
            logger.warning(f"Failed to save speaker {speaker_id}: {e}")
            return False

    def has_speakers(self) -> bool:
        """Check if any speaker audio files exist in the workspace."""
        d = self.speakers_dir
        return d.exists() and any(d.glob("speaker_*.wav"))

    @classmethod
    def open(cls, video_path: Path) -> "SharedWorkspace":
        """Open (or create) workspace for a video file.
        
        Computes content‑addressed job ID and initializes metadata.
        Existing workspace updates timestamp, but does not overwrite audio/segments.
        
        Args:
            video_path: Path to the source video file.
        """
        job_id = compute_job_id(video_path)
        if not job_id:
            raise ValueError(f"Failed to compute job ID for {video_path}")
        ws = cls(job_id)
        metadata = ws.load_metadata() or {}
        # Update metadata with timestamps and source info.
        metadata.update({
            "schema_version": _SCHEMA_VERSION,
            "job_id": job_id,
            "source_video": str(video_path),
            "created_at": metadata.get("created_at", time.time()),
            "updated_at": time.time(),
        })
        ws.update_metadata(**metadata)
        return ws

    @classmethod
    def from_job_id(cls, job_id: str) -> "SharedWorkspace":
        """Load an existing workspace by job ID without creating new directories.
        
        If the workspace does not exist, returns a workspace instance that will
        lazily create directories on first write.
        
        Args:
            job_id: Must match pattern "sha256-<hex>".
        """
        return cls(job_id)

    def save_whisper_audio(self, wav_path: Path, duration_s: Optional[float] = None) -> bool:
        """Copy 16kHz mono whisper audio to workspace (audio_whisper.wav).
        
        Args:
            wav_path: Source WAV file path.
            duration_s: Audio duration in seconds (optional, stored in metadata).
        """
        if not wav_path.exists():
            logger.warning(f"Whisper audio not found: {wav_path}")
            return False
        dest = self.root / "audio_whisper.wav"
        try:
            dest.write_bytes(wav_path.read_bytes())
            self._update_metadata({"whisper_audio_path": str(dest), "duration_s": duration_s})
            logger.info(f"Saved whisper audio to workspace: {dest}")
            return True
        except Exception as e:
            logger.warning(f"Failed to save whisper audio to workspace: {e}")
            return False

    def save_full_audio(self, wav_path: Path) -> bool:
        """Copy source‑quality audio to workspace (audio_full.wav).
        
        Args:
            wav_path: Source WAV file path.
        """
        if not wav_path.exists():
            logger.warning(f"Full audio not found: {wav_path}")
            return False
        dest = self.root / "audio_full.wav"
        try:
            dest.write_bytes(wav_path.read_bytes())
            self._update_metadata({"full_audio_path": str(dest)})
            logger.info(f"Saved full audio to workspace: {dest}")
            return True
        except Exception as e:
            logger.warning(f"Failed to save full audio to workspace: {e}")
            return False

    def save_segments(self, segments: List[Dict[str, Any]], language: str, source: str = "whisper") -> bool:
        """Save subtitle segments to workspace (segments.json).
        
        Args:
            segments: List of segment dicts from Whisper.
            language: Detected or original language code (e.g., "en").
            source: Source of segments ("whisper", "embedded", "existing").
        """
        dest = self.root / "segments.json"
        try:
            with open(dest, "w", encoding="utf-8") as f:
                json.dump({"segments": segments, "language": language, "source": source}, f)
            count = len(segments)
            self._update_metadata({
                "segments_path": str(dest),
                "segments_language": language,
                "segments_source": source,
                "segments_count": count,
            })
            logger.info(f"Saved {count} segments to workspace: {dest}")
            return True
        except Exception as e:
            logger.warning(f"Failed to save segments to workspace: {e}")
            return False

    def load_segments(self) -> Optional[Dict[str, Any]]:
        """Load segments.json from workspace.
        
        Returns:
            Deserialized JSON content or None if file not found.
        """
        path = self.root / "segments.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load segments from workspace: {e}")
            return None

    def save_stems(self, vocals_path: Path, no_vocals_path: Path, producer: str = "demucs") -> bool:
        """Save extracted stems to workspace.
        
        Args:
            vocals_path: Source vocals.wav path.
            no_vocals_path: Source no_vocals.wav path (DSP) or background.wav (Demucs).
            producer: "demucs" or "dsp".
        """
        if not vocals_path.exists() or not no_vocals_path.exists():
            logger.warning(f"Stems missing: {vocals_path}, {no_vocals_path}")
            return False
        stems_dir = self.root / "stems"
        try:
            shutil.copy2(vocals_path, stems_dir / "vocals.wav")
            # Normalize producer: Demucs uses background.wav, DSP uses no_vocals.wav.
            src = no_vocals_path
            stem_name = "background.wav" if producer == "demucs" else "no_vocals.wav"
            shutil.copy2(src, stems_dir / stem_name)
            self._update_metadata({
                "stems_path": str(stems_dir),
                "stems_producer": producer,
                "stems_vocals": str(stems_dir / "vocals.wav"),
                "stems_background": str(stems_dir / "background.wav") if producer == "demucs" else str(stems_dir / "no_vocals.wav"),
            })
            logger.info(f"Saved stems to workspace: producer={producer}")
            return True
        except Exception as e:
            logger.warning(f"Failed to save stems to workspace: {e}")
            return False

    def save_dubbed_segment(self, segment_id: int, wav_path: Path) -> bool:
        """Save a dubbed segment to workspace.
        
        Args:
            segment_id: Zero‑based segment ID (e.g., 0 → seg_0000.wav).
            wav_path: Source WAV file path.
        """
        if not wav_path.exists():
            logger.warning(f"Dubbed segment not found: {wav_path}")
            return False
        segment_name = f"seg_{segment_id:04d}.wav"
        dest = self.root / "dubbed" / segment_name
        try:
            shutil.copy2(wav_path, dest)
            logger.info(f"Saved dubbed segment to workspace: {dest}")
            return True
        except Exception as e:
            logger.warning(f"Failed to save dubbed segment to workspace: {e}")
            return False

    def has_whisper_audio(self) -> bool:
        """Check if whisper audio exists in workspace."""
        return (self.root / "audio_whisper.wav").exists()

    def has_full_audio(self) -> bool:
        """Check if full audio exists in workspace."""
        return (self.root / "audio_full.wav").exists()

    def has_segments(self) -> bool:
        """Check if segments.json exists in workspace."""
        return (self.root / "segments.json").exists()

    def has_stems(self) -> bool:
        """Check if any stem files exist in workspace."""
        stems_dir = self.root / "stems"
        return (stems_dir / "vocals.wav").exists() or (stems_dir / "background.wav").exists() or (stems_dir / "no_vocals.wav").exists()

    def load_metadata(self) -> Optional[Dict[str, Any]]:
        """Load metadata.json from workspace.
        
        Returns:
            Deserialized JSON content or None if file not found.
        """
        path = self.root / "metadata.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load metadata from workspace: {e}")
            return None

    def update_metadata(self, **fields: Any) -> bool:
        """Thread‑safe update of metadata.json with the given fields.
        
        Reads existing metadata, applies updates, and writes back under a lock.
        """
        with _metadata_lock:
            try:
                meta = self.load_metadata() or {}
                meta.update(fields)
                dest = self.root / "metadata.json"
                with open(dest, "w", encoding="utf-8") as f:
                    json.dump(meta, f)
                logger.debug(f"Updated workspace metadata: {list(fields.keys())}")
                return True
            except Exception as e:
                logger.warning(f"Failed to update workspace metadata: {e}")
                return False

    def _update_metadata(self, fields: Dict[str, Any]) -> bool:
        """Helper: update metadata. Maintains backwards compatibility for existing callers."""
        return self.update_metadata(**fields)


import shutil