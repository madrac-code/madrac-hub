# DUBS HTTP API — Contract v1

**Status**: DRAFT  
**Last updated**: 2026-06-26  
**Component**: madrac-dubs  
**Consumers**: madrac-subs (Phase 1), madrac-hub (orchestration)

---

## Base URL

```
http://127.0.0.1:5000
```

The API server is a local Flask process. It MUST be reachable at
`127.0.0.1:5000` before any endpoint is called.

---

## Endpoints

### `POST /dubbing` — Submit a dubbing job

#### Request

```json
{
  "video_path": "C:\\Users\\user\\video.mp4",
  "srt_path":   "C:\\Users\\user\\subtitles.srt",
  "output_path": "C:\\Users\\user\\video_dubbed.mkv",
  "config": {
    "language":      "es",
    "voice":         "female",
    "reduce_vocals": 0.3
  }
}
```

**Fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `video_path` | string | ✅ | — | Absolute path to input video file |
| `srt_path` | string | ✅ | — | Absolute path to input SRT file |
| `output_path` | string | ❌ | `<video_dir>/<video_stem>_dubbed.mkv` | Absolute path for output MKV |
| `config.language` | string | ❌ | `"es"` | Target language code |
| `config.voice` | string | ❌ | `"female"` | Voice gender: `female`, `male`, `neutral` |
| `config.reduce_vocals` | float | ❌ | `0.7` | Vocal reduction 0.0–1.0 |
| `config.tts_engine` | string | ❌ | `"edge"` | TTS backend: `edge`, `elevenlabs`, `pyttsx3` |
| `config.target_lufs` | float | ❌ | `-20.0` | LUFS loudness target |
| `config.hardcode_subs` | bool | ❌ | `false` | Burn subtitles into video |
| `config.output_tracks` | bool | ❌ | `true` | Separate audio tracks in MKV |

#### Response `200`

```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending"
}
```

#### Response `400`

```json
{
  "error": "Explicit error message describing what was invalid"
}
```

---

### `GET /dubbing/<job_id>` — Poll job status

#### Response `200`

```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "generating_tts",
  "progress_pct": 45,
  "message": "Generated TTS for 15 of 32 segments",
  "error": null,
  "output_path": "C:\\Users\\user\\video_dubbed.mkv"
}
```

**Possible status values (in order):**

| Status | Meaning |
|--------|---------|
| `pending` | Job created, waiting to start |
| `validating` | Checking input files |
| `extracting_audio` | FFmpeg extract audio from video |
| `generating_tts` | Edge TTS synthesis per segment |
| `reducing_vocals` | Center-channel cancellation |
| `mixing_audio` | Sync + normalize + mix |
| `exporting` | FFmpeg mux to output MKV |
| `completed` | Done. `output_path` contains the result |
| `failed` | Error. Check `error` field for details |

#### Response `404`

```json
{
  "error": "Job not found"
}
```

---

### `GET /health` — Health check

#### Response `200`

```json
{
  "status": "ok",
  "mode": "standalone"
}
```

**`mode` values:** `standalone` | `integrated`

---

## Versioning

This is **v1** of the DUBS HTTP API contract.

- Adding optional fields to request or response is NOT a breaking change.
- Changing a required field to optional is NOT a breaking change.
- Removing a field, adding a required field, or changing a response
  status code IS a breaking change.
- Breaking changes require a new endpoint path (`/v2/dubbing`).
  Old endpoints MUST remain operational during a deprecation period.

---

## Path Handling Rules

1. All file paths are passed as JSON strings.
2. Paths MUST be absolute. Relative paths are undefined behaviour.
3. The sender (madrac-subs) is responsible for providing valid paths.
4. The receiver (madrac-dubs) is responsible for escaping paths
   correctly before passing them to FFmpeg or any subsystem.
5. Paths with spaces, Unicode characters, or backslashes MUST be
   encoded as valid JSON strings (which the `json` module handles
   automatically in both Python and JavaScript).
6. The receiver SHOULD use `shlex.quote()` or equivalent before
   passing paths to shell commands.
