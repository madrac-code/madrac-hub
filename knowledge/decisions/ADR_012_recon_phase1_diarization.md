# ADR-012 — RECON Phase 1: Speaker Diarization into SharedWorkspace

**Date**: 2026-08-13
**Status**: Implemented
**Deciders**: Human
**Components affected**: RECON (new), SUBS, MCP

## Context

MADRAC needs speaker identity persisted per job. Phase 1 scope is
diarization only: given a workspace `job_id`, split the audio's voices,
persist one WAV per speaker and a machine-readable mapping. Voice
cloning (Coqui TTS / StyleTTS2), the custom "madrac" wakeword, the MUI
dubbing station (timeline/mixer) and the 3-channel editor are
explicitly OUT of scope (ADR-008 only lists them as future).

## Options Considered

| Option | Weight | License | GPU | Quality | Notes |
|--------|--------|---------|-----|---------|-------|
| pyannote.audio 3.x | ~heavy (torch already present) | MIT code, model license + HF token required | Recommended | Best (segmentation + clustering) | Token/license friction for a first phase |
| speechbrain (ECAPA-TDNN embeddings) | moderate | Apache-2.0 | Optional | Good | More deps (hyperpyyaml, HF hub); model download on first run |
| **resemblyzer 0.1.4** | light (~86MB model) | **MIT** | Optional (CPU ok) | Good enough for speaker separation | No token, no HF; embeddings 1.6s windows; already works with numpy 2.x in hub venv |

## Decision

**resemblyzer 0.1.4** for voice embeddings + **scikit-learn KMeans**
(already in venv) for clustering, K chosen by silhouette score over
cosine distance.

Rationale: lightest viable path — MIT license, no token, no GPU
requirement, verified import with numpy 2.4.6 / torch 2.12 in the hub
venv. Replacing the engine later (e.g. pyannote) is isolated behind
`_embed_frames()`/`_cluster_frames()`.

## File Contract in SharedWorkspace

Written by RECON Phase 1 (`madrac_recon.diarize.diarize_job`):

- `stems/speakers/speaker_N.wav` — one WAV per speaker (16 kHz mono
  PCM16): concatenation of that speaker's 0.5s turns with 10ms fades
  (documented choice: concatenated slices, not full-length aligned audio).
- `speakers.json` — machine-readable mapping:
  ```json
  {
    "schema_version": "1.0",
    "diarizer": "resemblyzer",
    "sample_rate": 16000,
    "source_audio": "<abs path>",
    "speaker_count": 2,
    "speakers": [
      {"speaker_id": "speaker_0", "name": "Speaker 1",
       "segments": [{"start": 0.0, "end": 3.2}]}
    ]
  }
  ```
- `metadata.json` updates (via `SharedWorkspace.update_metadata`):
  `artifacts.stems.speakers: true`, `speaker_count`, `speakers_json_path`,
  `diarizer`.

SharedWorkspace extension (minimal, documented in shared.py):
`speakers_dir` property, `save_speaker(speaker_id, wav_path)`,
`has_speakers()`. Artifact summaries in the workspace MCP tools now
include `speakers`.

## Pipeline

1. Resolve workspace (`SharedWorkspace.from_job_id`; `diarize_video`
   computes the content-addressed job_id). No workspace → clear error.
2. Source audio: `audio_full.wav` preferred, else `audio_whisper.wav`;
   none → clear error.
3. Embed with resemblyzer (1.6s windows / 0.5s hop / 16 kHz).
4. Cluster with KMeans (1..max_speakers), silhouette over cosine.
5. Reconstruct per-speaker clips, write WAVs, persist `speakers.json`
   + metadata.
6. Best-effort: failures return `{"error": ...}` via the MCP tool and
   never break SUBS/DUBS.

## MCP Integration

New tool `diarize_speakers(job_id?, video_path?, min_speakers?,
max_speakers?)` registered in `mcp/server.py`, `mcp/http_server.py`
tool_map and `mcp/tool_schemas.py` (21 tools total). Not added to the
MUI button whitelist — not a Phase 1 requirement.

## Out of Scope (explicit)

- Voice cloning (Coqui TTS / StyleTTS2) — future phase.
- Custom "madrac" wakeword training — future phase.
- MUI Phase 2 (timeline/mixer/keybindings) — separate track (ADR-011).
- 3-channel editor (background/dubbed/mix).
- Speaker ↔ subtitle segment mapping (Phase 2 of RECON).

## Consequences

- New hub dependency: `resemblyzer==0.1.4` (pinned in requirements-recon.txt,
  installed with `--no-deps` to avoid the obsolete `typing` backport that
  breaks PyInstaller; real deps are declared in requirements.txt).
- The pretrained encoder (16.3MB) is bundled into the PyInstaller exe
  (`collect_data_files('resemblyzer')`) — onefile temp dirs are not
  writable/persistent, so first-run download would not work there.
- Model is loaded per run; a long-running app could cache the encoder
  later (out of Phase 1).