# LLAVE-005 — Audio Device Limitations on Windows

**Date**: 2026-08-06
**Status**: Open
**Components**: MADRAC-ASISTENTE

## Problem

sounddevice/PortAudio blocking InputStream (sd.InputStream) fails
on Windows with most devices:
- MME: "Unanticipated host error" (error 1)
- WDM-KS: "Blocking API not supported yet" (error -9999)
- WASAPI: Only works at device's native sample rate (44100Hz for DroidCam,
  not the 16000Hz required by Whisper)

The Realtek mic (device 27, WDM-KS) cannot open in blocking mode.
DroidCam WASAPI (device 18) only supports 44100Hz.
No device on this machine supports 16000Hz in WASAPI shared mode.

## Root Cause

The assistant uses sd.InputStream() in blocking mode reading chunks.
This requires the device to support blocking mode + 16000Hz sample rate.
Most Windows audio drivers only expose this via MME (unreliable) or
require WASAPI exclusive mode (locks the device).

## Workaround (future)

Replace sd.InputStream() blocking loop with sd.rec() + scipy resample:
  1. Record at device's native rate (44100Hz)
  2. Resample to 16000Hz for openwakeword/Whisper
  3. This works regardless of host API

Or: use sounddevice callback mode instead of blocking mode.

## Current State

Assistant audio input is non-functional on this machine due to
audio device constraints. The code is correct — the hardware
environment is the blocker.

## References

- ADR-009 (assistant integration)
- src/madrac_asistente/core/audio.py — esperar_wakeword()