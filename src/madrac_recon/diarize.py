"""RECON Phase 1 — speaker diarization into SharedWorkspace.

Pipeline:
  1. Resolve workspace from job_id (or compute from video path).
  2. Pick source audio: audio_full.wav preferred, else audio_whisper.wav.
  3. Embed voice frames with resemblyzer (1.6s windows, 0.5s hop, 16kHz).
  4. Cluster embeddings with scikit-learn KMeans, K chosen by
     silhouette score over cosine distance.
  5. Reconstruct one WAV per speaker (concatenated 0.5s turns, 10ms fades).
  6. Persist: stems/speakers/speaker_N.wav, speakers.json, metadata.json.

Best-effort: never raises into the ecosystem — callers may catch
ValueError for clear user-facing errors; the MCP tool wraps everything.
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

TARGET_SR = 16000
WINDOW_S = 1.6        # resemblyzer embedding window size
HOP_S = 0.5           # embedding hop between windows
MAX_SPEAKERS_DEFAULT = 8
SILENCE_GAP_S = 0.5   # merge turns of the same speaker separated by less


def _workspace_module() -> Any:
    """Import SharedWorkspace (madrac_subs) without a hard dependency."""
    from madrac.workspace.shared import SharedWorkspace, compute_job_id  # noqa: PLC0415

    return SharedWorkspace, compute_job_id


def _resolve_workspace(job_id: str) -> Any:
    """Open an existing workspace; error clearly if it does not exist."""
    SharedWorkspace, _ = _workspace_module()
    ws = SharedWorkspace.from_job_id(job_id)
    if not (ws.root / "metadata.json").exists():
        raise ValueError(
            f"Workspace {job_id} not found — run SUBS transcription first"
        )
    return ws


def _pick_audio(ws: Any) -> Path:
    """Prefer full-quality audio; fall back to whisper audio."""
    for name in ("audio_full.wav", "audio_whisper.wav"):
        p = ws.root / name
        if p.exists():
            return p
    raise ValueError(
        f"No audio in workspace {ws.job_id} "
        "(need audio_full.wav or audio_whisper.wav)"
    )


def _embed_frames(wav: np.ndarray) -> np.ndarray:
    """Compute voice embeddings for sliding windows of the audio."""
    from resemblyzer import VoiceEncoder  # noqa: PLC0415

    encoder = VoiceEncoder()
    frames = encoder.embed_frames(wav)
    return frames


def _cluster_frames(
    embeds: np.ndarray, min_speakers: int, max_speakers: int
) -> np.ndarray:
    """KMeans over cosine distance, K picked by silhouette score."""
    from sklearn.cluster import KMeans  # noqa: PLC0415
    from sklearn.metrics import silhouette_score  # noqa: PLC0415

    n = len(embeds)
    if n <= 1 or max_speakers < 2:
        return np.zeros(n, dtype=int)

    k_max = min(max_speakers, n)
    k_min = max(1, min(min_speakers, k_max))

    best: Optional[tuple[float, np.ndarray]] = None
    for k in range(k_min, k_max + 1):
        labels = KMeans(n_clusters=k, n_init=3, random_state=0).fit_predict(embeds)
        if k == 1:
            score = 0.0
        elif len(set(labels)) < 2:
            score = -1.0
        else:
            score = silhouette_score(embeds, labels, metric="cosine")
        if best is None or score > best[0]:
            best = (score, labels)

    return best[1]


def _reconstruct_per_speaker(
    wav: np.ndarray, labels: np.ndarray
) -> dict[int, np.ndarray]:
    """Split audio into per-speaker clips.

    Each 0.5s chunk inherits the label of the window that starts there;
    chunks are concatenated per speaker with 10ms linear fades to avoid
    clicks at turn boundaries.
    """
    sr = TARGET_SR
    chunk = int(HOP_S * sr)
    fade = int(0.010 * sr)

    clips: dict[int, list[np.ndarray]] = {lab: [] for lab in set(labels)}
    for i, lab in enumerate(labels):
        start = i * chunk
        end = min(start + chunk, len(wav))
        piece = wav[start:end]
        if len(piece) > 2 * fade and fade > 0:
            piece = piece.copy()
            piece[:fade] *= np.linspace(0.0, 1.0, fade)
            piece[-fade:] *= np.linspace(1.0, 0.0, fade)
        clips[lab].append(piece)

    return {lab: np.concatenate(parts) for lab, parts in clips.items()}


def _turn_times(labels: np.ndarray) -> dict[int, list[dict[str, float]]]:
    """Map each speaker to merged contiguous turns (seconds)."""
    chunk = HOP_S
    result: dict[int, list[dict[str, float]]] = {}
    for lab in set(labels):
        idx = np.flatnonzero(labels == lab)
        if len(idx) == 0:
            continue
        turns: list[dict[str, float]] = []
        start = float(idx[0]) * chunk
        end = float(idx[0] + 1) * chunk
        for i in idx[1:]:
            if i * chunk - end <= SILENCE_GAP_S:
                end = float(i + 1) * chunk
            else:
                turns.append({"start": round(start, 2), "end": round(end, 2)})
                start = float(i) * chunk
                end = float(i + 1) * chunk
        turns.append({"start": round(start, 2), "end": round(end, 2)})
        result[int(lab)] = turns
    return result


def _write_speaker_wavs(
    ws: Any, clips: dict[int, np.ndarray]
) -> tuple[list[str], dict[int, int]]:
    """Write speaker_N.wav files into the workspace; return paths + mapping."""
    import soundfile as sf  # noqa: PLC0415

    paths: list[str] = []
    order = sorted(clips)  # stable ordering by cluster label
    for lab in order:
        audio = clips[lab]
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = Path(f.name)
        try:
            sf.write(str(tmp), (audio * 32767.0).astype(np.int16), TARGET_SR)
            if ws.save_speaker(int(lab), tmp):
                paths.append(str(ws.speakers_dir / f"speaker_{int(lab)}.wav"))
        finally:
            tmp.unlink(missing_ok=True)
    return paths, {int(lab): int(lab) for lab in order}


def _persist(
    ws: Any,
    result: "DiarizationResult",
    labels: np.ndarray,
    source_audio: str,
) -> dict[str, Any]:
    """Write speakers.json + metadata.json, return the public summary."""
    turns = _turn_times(labels)
    speaker_count = len(result.speaker_paths)

    speakers = [
        {
            "speaker_id": f"speaker_{lab}",
            "name": f"Speaker {i + 1}",
            "segments": turns.get(lab, []),
        }
        for i, lab in enumerate(sorted(set(labels)))
    ]

    payload = {
        "schema_version": "1.0",
        "diarizer": result.diarizer,
        "sample_rate": TARGET_SR,
        "source_audio": source_audio,
        "speaker_count": speaker_count,
        "speakers": speakers,
    }
    speakers_path = ws.root / "speakers.json"
    speakers_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    ws.update_metadata(
        artifacts={"stems": {"speakers": True}},
        speaker_count=speaker_count,
        speakers_json_path=str(speakers_path),
        diarizer=result.diarizer,
    )

    return {
        "job_id": ws.job_id,
        "status": "done",
        "speaker_count": speaker_count,
        "speaker_paths": result.speaker_paths,
        "speakers_json": str(speakers_path),
        "diarizer": result.diarizer,
        "sample_rate": TARGET_SR,
    }


def diarize_job(
    job_id: str,
    min_speakers: int = 1,
    max_speakers: int = MAX_SPEAKERS_DEFAULT,
) -> dict[str, Any]:
    """Diarize speakers for an existing workspace job."""
    import librosa  # noqa: PLC0415

    ws = _resolve_workspace(job_id)
    audio_path = _pick_audio(ws)

    wav, _ = librosa.load(str(audio_path), sr=TARGET_SR, mono=True)
    if len(wav) < int(WINDOW_S * TARGET_SR):
        raise ValueError(
            f"Audio too short for diarization: {len(wav) / TARGET_SR:.1f}s"
        )

    embeds = _embed_frames(wav)
    labels = _cluster_frames(embeds, min_speakers, max_speakers)
    clips = _reconstruct_per_speaker(wav, labels)

    from .models import DiarizationResult  # noqa: PLC0415

    paths, _ = _write_speaker_wavs(ws, clips)
    result = DiarizationResult(
        job_id=ws.job_id,
        speaker_count=len(paths),
        speaker_paths=paths,
        source_audio=str(audio_path),
    )
    summary = _persist(ws, result, labels, str(audio_path))
    logger.info("Diarization done for %s: %d speakers", ws.job_id, len(paths))
    return summary


def diarize_video(
    video_path: str,
    min_speakers: int = 1,
    max_speakers: int = MAX_SPEAKERS_DEFAULT,
) -> dict[str, Any]:
    """Open (or create) a workspace from a video path, then diarize."""
    SharedWorkspace, compute_job_id = _workspace_module()
    job_id = compute_job_id(Path(video_path))
    if not job_id:
        raise ValueError(f"Could not compute job ID for {video_path}")
    ws = SharedWorkspace.from_job_id(job_id)
    if not (ws.root / "metadata.json").exists():
        raise ValueError(
            f"Workspace {job_id} not found — run SUBS transcription first"
        )
    return diarize_job(job_id, min_speakers=min_speakers,
                       max_speakers=max_speakers)