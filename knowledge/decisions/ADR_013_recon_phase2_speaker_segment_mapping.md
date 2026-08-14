# ADR-013: RECON Phase 2 — Speaker-to-Subtitle Segment Mapping

## Status
Accepted

## Context
Phase 1 produced two independent artifacts per workspace job:
- `segments.json` — subtitle segments from SUBS (Whisper + optional translation): `{start, end, text}` × N
- `speakers.json` — diarization from RECON: `speaker_id`, `name`, `segments[{start, end}]` × M speakers

These two timelines are not yet linked. Downstream consumers (export SRT with speaker tags, dubbing with per-speaker TTS voices, storyboard with character identities) need to know **which speaker spoke each subtitle segment**.

## Decision
Add a new MCP tool `map_speakers_to_segments(job_id)` that:
- Reads `segments.json` and `speakers.json` from the workspace
- For each subtitle segment, computes temporal overlap with every speaker's turn intervals
- Assigns the speaker with **maximum total overlap** (sum of intersection durations across all turns of that speaker)
- Fallback: if overlap = 0 (segment falls in a gap between turns), assign the **closest speaker in time** (minimum distance from segment center to any turn boundary)
- Confidence = `overlap_duration / segment_duration` (0.0 if fallback used)
- Writes `speaker_segments.json` (new file, **does not modify `segments.json`** — keeps SUBS and RECON decoupled)
- Updates `metadata.json` → `artifacts.stems.speaker_segments: true`, `speaker_segments_path`, `speaker_mapped_count`

Schema of `speaker_segments.json`:
```json
{
  "schema_version": "1.0",
  "job_id": "sha256-...",
  "mapped_at": 1786600000.0,
  "segments": [
    {
      "segment_index": 0,
      "start": 0.0,
      "end": 4.379,
      "text": "Este castelo...",
      "speaker_id": "speaker_1",
      "speaker_name": "Speaker 2",
      "confidence": 0.92
    }
  ],
  "unmapped": 0,
  "total_confidence": 0.87
}
```

## Rationale
- **New file, not in-place edit**: `segments.json` stays the source of truth for subtitle text/timing; downstream exporters (SRT, etc.) remain unchanged. Consumers opt in to speaker info by reading `speaker_segments.json`.
- **Max overlap (not threshold)**: A fixed threshold (e.g., "overlap > 50%") fails on short segments or dense dialogue. Max overlap naturally picks the dominant speaker per segment; confidence quantifies ambiguity.
- **Fallback to closest**: Guarantees every segment gets a speaker (no `null`), critical for dubbing pipelines that need a voice per line. Confidence=0 flags low-trust assignments for human review.
- **MCP tool (not inline in diarize)**: Separation of concerns. Diarization produces speakers; mapping is a separate step that can be re-run if segments change (re-translate, re-segment).
- **Artifact pattern**: Follows existing `artifacts.stems.*` convention in `metadata.json`; `get_workspace_info` and `list_workspaces` surface it automatically.

## Consequences
- New hub dependency: none (pure Python, uses existing `shared.py` workspace).
- New MCP tool: `map_speakers_to_segments` (total tools: 22).
- New artifact: `speaker_segments.json` per job.
- Phase 3 (Storyboard / character identity) will consume `speaker_segments.json` to bind visual characters to speaker identities.

## Out of Scope
- Speaker renaming (already exists: `rename_speaker` tool).
- Re-segmentation to align with speaker turns (keep SUBS segmentation).
- Multi-speaker segments (one segment → one speaker; if true overlap is split, confidence drops).