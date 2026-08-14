"""Speaker-to-subtitle segment mapping for RECON Phase 2."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .models import DiarizationResult, SpeakerSegment


@dataclass
class MappedSegment:
    """A subtitle segment enriched with speaker info."""
    segment_index: int
    start: float
    end: float
    text: str
    speaker_id: str
    speaker_name: str
    confidence: float


@dataclass
class MappingResult:
    """Result of speaker-segment mapping."""
    job_id: str
    mapped_at: float
    segments: list[MappedSegment]
    unmapped: int
    total_confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "job_id": self.job_id,
            "mapped_at": self.mapped_at,
            "segments": [asdict(s) for s in self.segments],
            "unmapped": self.unmapped,
            "total_confidence": round(self.total_confidence, 3),
        }


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    """Duration of intersection between two intervals."""
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _distance_to_turns(seg_center: float, turns: list[dict[str, float]]) -> float:
    """Minimum distance from segment center to any turn boundary."""
    if not turns:
        return float("inf")
    dists = []
    for t in turns:
        dists.append(abs(seg_center - t["start"]))
        dists.append(abs(seg_center - t["end"]))
    return min(dists)


def map_speakers_to_segments(
    segments_data: dict[str, Any],
    speakers_data: dict[str, Any],
) -> MappingResult:
    """
    Map each subtitle segment to the speaker with maximum temporal overlap.

    Args:
        segments_data: parsed segments.json (has "segments" list with start/end/text)
        speakers_data: parsed speakers.json (has "speakers" list with speaker_id, name, segments)

    Returns:
        MappingResult with mapped segments, confidence scores, and totals.
    """
    sub_segments = segments_data.get("segments", [])
    if not sub_segments:
        return MappingResult(
            job_id="",
            mapped_at=time.time(),
            segments=[],
            unmapped=0,
            total_confidence=0.0,
        )

    # Build list of (speaker_id, speaker_name, turn_intervals) for each speaker
    speaker_turns = []
    for spk in speakers_data.get("speakers", []):
        turns = [{"start": s["start"], "end": s["end"]} for s in spk.get("segments", [])]
        speaker_turns.append((spk["speaker_id"], spk["name"], turns))

    mapped = []
    total_conf = 0.0
    unmapped = 0

    for idx, seg in enumerate(sub_segments):
        s_start = float(seg["start"])
        s_end = float(seg["end"])
        seg_dur = s_end - s_start
        seg_center = (s_start + s_end) / 2.0

        best_spk_id = ""
        best_spk_name = ""
        best_overlap = 0.0

        # Find speaker with max total overlap
        for spk_id, spk_name, turns in speaker_turns:
            overlap_sum = sum(_overlap(s_start, s_end, t["start"], t["end"]) for t in turns)
            if overlap_sum > best_overlap:
                best_overlap = overlap_sum
                best_spk_id = spk_id
                best_spk_name = spk_name

        if best_overlap > 0.0:
            confidence = best_overlap / seg_dur if seg_dur > 0 else 0.0
            used_fallback = False
        else:
            # Fallback: closest speaker in time
            best_dist = float("inf")
            for spk_id, spk_name, turns in speaker_turns:
                d = _distance_to_turns(seg_center, turns)
                if d < best_dist:
                    best_dist = d
                    best_spk_id = spk_id
                    best_spk_name = spk_name
            confidence = 0.0
            used_fallback = True
            unmapped += 1

        mapped.append(MappedSegment(
            segment_index=idx,
            start=s_start,
            end=s_end,
            text=seg.get("text", ""),
            speaker_id=best_spk_id,
            speaker_name=best_spk_name,
            confidence=round(confidence, 3),
        ))
        total_conf += confidence

    avg_conf = total_conf / len(mapped) if mapped else 0.0

    return MappingResult(
        job_id="",
        mapped_at=time.time(),
        segments=mapped,
        unmapped=unmapped,
        total_confidence=round(avg_conf, 3),
    )


def persist_mapping(ws: Any, result: MappingResult) -> dict[str, Any]:
    """
    Write speaker_segments.json and update metadata.json.
    Returns the public summary dict.
    """
    speakers_path = ws.root / "speaker_segments.json"
    speakers_path.write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Update metadata
    meta_path = ws.root / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.setdefault("artifacts", {}).setdefault("stems", {})["speaker_segments"] = True
    meta["speaker_segments_path"] = str(speakers_path)
    meta["speaker_mapped_count"] = len(result.segments)
    meta["speaker_mapping_confidence"] = result.total_confidence
    meta["updated_at"] = time.time()
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return {
        "job_id": result.job_id,
        "status": "done",
        "mapped_count": len(result.segments),
        "unmapped": result.unmapped,
        "total_confidence": result.total_confidence,
        "speaker_segments_path": str(speakers_path),
    }


def map_job(job_id: str) -> dict[str, Any]:
    """
    High-level: load workspace, read segments + speakers, map, persist.
    """
    from .diarize import _resolve_workspace  # noqa: PLC0415
    from madrac.workspace.shared import SharedWorkspace  # noqa: PLC0415

    ws = _resolve_workspace(job_id)

    # Load segments.json
    segments_path = ws.root / "segments.json"
    if not segments_path.exists():
        raise ValueError(f"segments.json not found in job {job_id} — run SUBS transcription first")
    segments_data = json.loads(segments_path.read_text(encoding="utf-8"))

    # Load speakers.json
    speakers_path = ws.root / "speakers.json"
    if not speakers_path.exists():
        raise ValueError(f"speakers.json not found in job {job_id} — run diarize_speakers first")
    speakers_data = json.loads(speakers_path.read_text(encoding="utf-8"))

    # Map
    result = map_speakers_to_segments(segments_data, speakers_data)
    result.job_id = job_id

    # Persist
    return persist_mapping(ws, result)