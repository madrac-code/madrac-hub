"""Time formatting utilities."""


def srt_timestamp(seconds: float) -> str:
    """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def vtt_timestamp(seconds: float) -> str:
    """Format seconds as VTT timestamp (HH:MM:SS.mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def ass_timestamp(seconds: float) -> str:
    """Format seconds as ASS timestamp (H:MM:SS.cc)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:01d}:{s:05.2f}"


def human_duration(seconds: float) -> str:
    """Format duration as human-readable (e.g. '1h 23m 45s')."""
    if seconds < 0:
        return "0s"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    parts = []
    if h > 0:
        parts.append(f"{h}h")
    if m > 0:
        parts.append(f"{m}m")
    if s > 0 or not parts:
        parts.append(f"{s}s")
    return " ".join(parts)


def estimate_transcription_time(duration_s: float, model: str = "base", vad: bool = True) -> float:
    """Estimate transcription wall time based on model factors."""
    factors = {"tiny": 0.2, "base": 0.4, "small": 0.8, "medium": 1.5}
    rtf = factors.get(model, 0.5)
    if vad:
        rtf *= 0.7
    return max(duration_s * rtf, 1.0)
