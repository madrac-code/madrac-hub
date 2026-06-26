# USE CASE 001 — SUBS → DUBS ("Dub Now")

**Status**: SPEC — pending implementation in madrac-subs  
**Phase**: Phase 1 (Runtime Foundation)  
**Contract**: `runtime/contracts/dubbing-api-v1.md`  
**Last updated**: 2026-06-26

---

## Description

A user has a video open in MADRAC-SUBS with subtitles loaded. They
want to generate an AI-dubbed version: the original audio is replaced
with synthesized speech in a target language, while background audio
(music, sound effects) is partially preserved.

The dubbing is performed by MADRAC-DUBS, a standalone engine that
accepts a video + SRT pair via HTTP API and returns a dubbed MKV.

This use case covers the integration path from SUBS to DUBS: launching
the DUBS engine on demand, submitting the job, tracking progress, and
presenting the result to the user.

---

## Preconditions

1. MADRAC-DUBS is installed on the same machine as MADRAC-SUBS.
   The executable path is known (configured or auto-detected).
2. MADRAC-SUBS has a video file open in its media player.
3. MADRAC-SUBS has subtitles loaded for that video (either
   transcribed, imported, or manually created).
4. The subtitles are in SRT format (or can be exported to SRT).

---

## Flow

### Step 1 — User triggers dubbing

User clicks a "Dub Now" button (or menu item) in the SUBS toolbar.
SUBS opens a dubbing configuration dialog with:

- Target language selector (default: Spanish)
- Voice selector (female / male / neutral)
- Vocal reduction slider (default: 0.3)

The user confirms the configuration.

### Step 2 — SUBS launches DUBS (if not running)

SUBS checks if DUBS is already running via `GET /health`.
If no response, SUBS launches:

```
madrac-dubbing.exe api --port 5000
```

as a background subprocess. SUBS waits for the health check to
succeed (timeout: 15 seconds, retry: every 1 second).

### Step 3 — SUBS submits the dubbing job

SUBS exports the current subtitles to a temporary SRT file (if not
already saved as SRT). Then SUBS calls:

```
POST /dubbing
{
  "video_path": "<current video path>",
  "srt_path":   "<exported SRT path>",
  "config": {
    "language":      "<selected language>",
    "voice":         "<selected voice>",
    "reduce_vocals": <slider value>
  }
}
```

SUBS receives a `job_id` in response.

### Step 4 — SUBS tracks progress

SUBS polls `GET /dubbing/<job_id>` every 2 seconds and updates a
progress bar in the UI showing:

- Current stage name (extracting_audio, generating_tts, etc.)
- Percentage complete (0–100)
- Current status message

The UI remains responsive during this polling (use QTimer or
background thread).

### Step 5 — DUBS completes the job

When `GET /dubbing/<job_id>` returns `status: "completed"`,
SUBS checks that the `output_path` file exists on disk.

### Step 6 — SUBS presents the result

SUBS loads the dubbed MKV into the media player. The user can
play it, seek, and compare with the original audio track.

SUBS optionally offers: "Replace original audio" or "Keep both tracks".

### Step 7 — Cleanup

SUBS terminates the DUBS subprocess (or keeps it running if another
job is expected soon). The temporary SRT file may be kept or deleted.

---

## Postconditions

1. A new MKV file exists at `output_path` with the dubbed audio.
2. The MKV contains multiple audio tracks: original + dubbed + voice-only.
3. SUBS has the dubbed video loaded and ready for playback.
4. If DUBS was launched by SUBS, it is terminated (unless configured
   otherwise).

---

## Error Handling

| Error | Detection | User-Facing Message | Action |
|-------|-----------|---------------------|--------|
| DUBS not installed | Health check fails 15s timeout | "Dubbing engine not found. Install madrac-dubs to use this feature." | Disable button, show info dialog |
| Video file missing | POST /dubbing returns 400 | "Video file not found." | Show error, return to SUBS |
| SRT file missing | POST /dubbing returns 400 | "Subtitle file not found." | Show error, return to SUBS |
| DUBS crashes mid-job | Poll request fails (connection refused) | "Dubbing engine stopped unexpectedly." | Show error, terminate process |
| Duplication: output path collision | output_path already exists | "Output file already exists. Overwrite?" | Ask user before overwriting |
| Job fails (pipeline error) | status: "failed" | "Dubbing failed: <error message>" | Show error, clean up |
| Timeout (>10 min) | No completion within 600s | "Dubbing timed out. The video may be too long." | Terminate DUBS, show error |
| FFmpeg not found | (detected in POST response or health) | "FFmpeg is required for dubbing." | Guide user to install FFmpeg |
| Port 5000 in-use by non-DUBS | Health check returns unexpected response | "Port 5000 is in use by another application." | Ask user to close the other app |

---

## Files Involved

| File | Role | Owner |
|------|------|-------|
| `<video>.mp4` | Input video | SUBS user workspace |
| `<video>.srt` | Input subtitles | SUBS (exported or user-provided) |
| `<video>_dubbed.mkv` | Output dubbed video | DUBS writes; SUBS reads |
| `madrac-dubbing.exe` | DUBS executable | Installed alongside SUBS or separately |
| `~/.madrac/madrac-dubbing.json` | DUBS user config | DUBS creates/reads |

---

## Notes

- The DUBS executable path should be configurable in SUBS settings
  with a reasonable default (same directory as SUBS exe, or
  `C:\Program Files\MADRAC\madrac-dubbing.exe`).
- The integration test script at `development/tools/dubs_integration_test.py`
  validates this exact flow without the SUBS GUI.
- This spec does NOT define how DUBS is installed or updated.
  That is out of scope for this use case.
