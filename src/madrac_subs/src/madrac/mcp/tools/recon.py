"""RECON MCP tools — speaker diarization persisted in SharedWorkspace.

Diarization is best-effort: failures return {"error": ...} and never
break SUBS/DUBS pipelines.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# madrac_recon lives at the monorepo src/ root (sibling of madrac_subs).
_SRC_ROOT = Path(__file__).resolve().parents[5]
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from madrac_recon import diarize as recon_diarize  # noqa: E402


def diarize_speakers(app_state: dict[str, Any]):
    """Diarize speakers for a job and persist them in SharedWorkspace."""
    async def _diarize_speakers(
        job_id: str | None = None,
        video_path: str | None = None,
        min_speakers: int = 1,
        max_speakers: int = recon_diarize.MAX_SPEAKERS_DEFAULT,
    ) -> dict[str, Any]:
        """
        Diarize speakers for an existing workspace job.

        Persists stems/speakers/speaker_N.wav, speakers.json and updates
        metadata.json (artifacts.stems.speakers, speaker_count).

        Args:
            job_id: Workspace job ID (sha256-<hex>). Mutually exclusive
                    with video_path.
            video_path: Absolute path to the source video (computes job_id).
            min_speakers: Minimum number of speakers to look for.
            max_speakers: Maximum number of speakers to look for.

        Returns:
            {"job_id", "status", "speaker_count", "speaker_paths",
             "speakers_json", "diarizer", "sample_rate"}
        """
        try:
            if not job_id and not video_path:
                return {"error": "Provide job_id or video_path"}
            if job_id and video_path:
                return {"error": "Provide only one of job_id or video_path"}
            if video_path:
                return recon_diarize.diarize_video(
                    video_path,
                    min_speakers=min_speakers,
                    max_speakers=max_speakers,
                )
            return recon_diarize.diarize_job(
                job_id,
                min_speakers=min_speakers,
                max_speakers=max_speakers,
            )
        except Exception as e:
            return {"error": str(e)}

    return _diarize_speakers