"""Real-media integration tests for media.py (requires ffmpeg in PATH).

Marked @pytest.mark.real — excluded from normal suite via pyproject.toml.
Run with: pytest -m real
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from madrac.utils.media import (
    mux_subtitles,
    demux_subtitles,
    detect_subtitles,
    probe_media,
    strip_subtitles,
)

pytestmark = pytest.mark.real

SRT_CONTENT = """1
00:00:01,000 --> 00:00:03,000
Linea uno

2
00:00:05,000 --> 00:00:07,000
Linea dos

3
00:00:10,000 --> 00:00:12,000
Linea tres

4
00:00:14,000 --> 00:00:16,000
Linea cuatro

5
00:00:18,000 --> 00:00:20,000
Linea cinco
"""


@pytest.fixture(scope="module")
def ffmpeg_available():
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("ffmpeg/ffprobe not in PATH")
    return ffmpeg, ffprobe


@pytest.fixture(scope="module")
def synthetic_video(ffmpeg_available):
    ffmpeg, _ = ffmpeg_available
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test_video.mp4"
        subprocess.run(
            [
                ffmpeg, "-f", "lavfi", "-i",
                "testsrc2=duration=10:size=320x240:rate=15",
                "-f", "lavfi", "-i",
                "sine=frequency=440:duration=10",
                "-c:v", "libx264", "-c:a", "aac",
                "-shortest", "-y", str(out),
            ],
            capture_output=True, check=True,
        )
        yield out


class TestRealMuxRoundtrip:
    def test_probe_before_mux(self, synthetic_video):
        info = probe_media(str(synthetic_video))
        assert info["video_streams"] == 1
        assert info["audio_streams"] == 1
        assert info["subtitle_streams"] == 0
        assert info["container"] == ".mp4"

    def test_mux_adds_subtitle_stream(self, synthetic_video):
        srt = synthetic_video.with_suffix(".srt")
        srt.write_text(SRT_CONTENT, encoding="utf-8")
        muxed = Path(mux_subtitles(str(synthetic_video), str(srt), language="spa"))
        assert muxed.exists()
        assert muxed.name == synthetic_video.name

        info = probe_media(str(muxed))
        assert info["subtitle_streams"] == 1
        assert info["subtitle_languages"] == ["spa"]

    def test_detect_after_mux(self, synthetic_video):
        muxed = synthetic_video
        if not muxed.exists():
            pytest.skip("muxed file not found — run test_mux_adds_subtitle_stream first")
        tracks = detect_subtitles(str(muxed))
        assert len(tracks) >= 1
        subs = [t for t in tracks if t.get("codec") in ("mov_text", "srt", "webvtt")]
        assert len(subs) >= 1
        assert subs[0]["language"] == "spa"

    def test_demux_roundtrip(self, synthetic_video):
        muxed = synthetic_video
        if not muxed.exists():
            pytest.skip("muxed file not found")
        extracted = demux_subtitles(str(muxed), output_dir=str(muxed.parent))
        assert len(extracted) >= 1
        spa = [p for p in extracted if "spa" in Path(p).stem]
        assert len(spa) >= 1
        content = Path(spa[0]).read_text(encoding="utf-8")
        assert "Linea uno" in content
        assert "Linea cinco" in content

    def test_strip_removes_subtitles(self, synthetic_video):
        muxed = synthetic_video
        if not muxed.exists():
            pytest.skip("muxed file not found")
        cleaned = Path(strip_subtitles(str(muxed)))
        assert cleaned.exists()
        info = probe_media(str(cleaned))
        assert info["subtitle_streams"] == 0

    def test_full_cycle(self, synthetic_video):
        srt = synthetic_video.with_suffix(".srt")
        if not srt.exists():
            srt.write_text(SRT_CONTENT, encoding="utf-8")

        muxed = Path(mux_subtitles(str(synthetic_video), str(srt), language="spa"))
        tracks = detect_subtitles(str(muxed))
        assert len(tracks) >= 1

        extracted = demux_subtitles(str(muxed), output_dir=str(muxed.parent))
        assert len(extracted) >= 1
        content = Path(extracted[0]).read_text(encoding="utf-8")
        assert content.strip().endswith("cinco")

        cleaned = Path(strip_subtitles(str(muxed)))
        info = probe_media(str(cleaned))
        assert info["subtitle_streams"] == 0
