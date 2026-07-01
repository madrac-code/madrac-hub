"""Tests for utils/media.py and pipeline/stages/mux.py."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from madrac.utils.media import (
    mux_subtitles,
    demux_subtitles,
    detect_subtitles,
    strip_subtitles,
    lang_639_2b,
    probe_media,
)
from madrac.pipeline.stages.mux import MuxStage
from madrac.pipeline.stages.base import StageResult


class TestLangMapping:
    def test_known_codes(self):
        assert lang_639_2b("es") == "spa"
        assert lang_639_2b("en") == "eng"
        assert lang_639_2b("pt") == "por"

    def test_unknown_code(self):
        assert lang_639_2b("xx") == "und"

    def test_empty_code(self):
        assert lang_639_2b("") == "und"


class TestMuxSubtitle:
    @patch("madrac.utils.media.resolve_executable")
    @patch("madrac.utils.media._srun")
    def test_mux_success(self, mock_run, mock_resolve):
        mock_resolve.return_value = "ffmpeg"
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "test.mp4"
            vid.write_text("video")
            srt = Path(tmp) / "test.srt"
            srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nhello")
            out = mux_subtitles(str(vid), str(srt))
            assert out == str(vid)

    @patch("madrac.utils.media.resolve_executable")
    @patch("madrac.utils.media._srun")
    def test_mux_ffmpeg_failure(self, mock_run, mock_resolve):
        mock_resolve.return_value = "ffmpeg"
        mock_run.return_value = MagicMock(returncode=1, stderr="error")

        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "test.mp4"
            vid.write_text("video")
            srt = Path(tmp) / "test.srt"
            srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nhello")
            with pytest.raises(RuntimeError, match="ffmpeg mux failed"):
                mux_subtitles(str(vid), str(srt))

    def test_mux_video_not_found(self):
        with pytest.raises(FileNotFoundError, match="Video not found"):
            mux_subtitles("nonexistent.mp4", "doesntmatter.srt")

    def test_mux_srt_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "test.mp4"
            vid.write_text("video")
            with pytest.raises(FileNotFoundError, match="SRT not found"):
                mux_subtitles(str(vid), "nonexistent.srt")

    @patch("madrac.utils.media.resolve_executable")
    @patch("madrac.utils.media._srun")
    def test_mux_no_ffmpeg(self, mock_run, mock_resolve):
        mock_resolve.return_value = None

        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "test.mp4"
            vid.write_text("video")
            srt = Path(tmp) / "test.srt"
            srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nhello")
            with pytest.raises(RuntimeError, match="ffmpeg not found"):
                mux_subtitles(str(vid), str(srt))

    @patch("madrac.utils.media.resolve_executable")
    @patch("madrac.utils.media._srun")
    def test_mux_custom_output(self, mock_run, mock_resolve):
        mock_resolve.return_value = "ffmpeg"
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "test.mp4"
            vid.write_text("video")
            srt = Path(tmp) / "test.srt"
            srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nhello")
            out_path = str(Path(tmp) / "custom_out.mp4")
            result = mux_subtitles(str(vid), str(srt), output_path=out_path)
            assert result == str(vid)

    @patch("madrac.utils.media.resolve_executable")
    @patch("madrac.utils.media._srun")
    def test_mux_mkv_codec(self, mock_run, mock_resolve):
        mock_resolve.return_value = "ffmpeg"
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "test.mkv"
            vid.write_text("video")
            srt = Path(tmp) / "test.srt"
            srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nhello")
            mux_subtitles(str(vid), str(srt))
            cmd = mock_run.call_args[0][0]
            idx = cmd.index("-c:s") + 1
            assert cmd[idx] == "srt"


class TestDetectSubtitles:
    @patch("madrac.utils.media.detect_subtitle_tracks")
    def test_detect_success(self, mock_detect):
        mock_detect.return_value = [
            {"index": 0, "codec": "srt", "language": "eng"},
        ]
        result = detect_subtitles("test.mp4")
        assert len(result) == 1
        assert result[0]["language"] == "eng"

    @patch("madrac.utils.media.detect_subtitle_tracks")
    def test_detect_no_tracks(self, mock_detect):
        mock_detect.return_value = []
        result = detect_subtitles("test.mp4")
        assert result == []

    @patch("madrac.utils.media.detect_subtitle_tracks")
    def test_detect_multiple(self, mock_detect):
        mock_detect.return_value = [
            {"index": 0, "codec": "srt", "language": "eng"},
            {"index": 1, "codec": "srt", "language": "spa"},
        ]
        result = detect_subtitles("test.mp4")
        assert len(result) == 2


class TestProbeMedia:
    def test_file_not_found(self):
        result = probe_media("nonexistent.mp4")
        assert result["video_streams"] == 0
        assert result["subtitle_streams"] == 0
        assert result["container"] == ".mp4"

    @patch("madrac.utils.media.resolve_executable")
    def test_no_ffprobe(self, mock_resolve):
        mock_resolve.return_value = None
        result = probe_media("some.mp4")
        assert result["subtitle_streams"] == 0

    @patch("madrac.utils.media.subprocess.run")
    @patch("madrac.utils.media.resolve_executable")
    def test_parses_streams(self, mock_resolve, mock_run):
        mock_resolve.return_value = "ffprobe"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "streams": [
                    {"index": 0, "codec_type": "video"},
                    {"index": 1, "codec_type": "audio"},
                    {"index": 2, "codec_type": "subtitle",
                     "tags": {"language": "spa"}},
                ]
            })
        )
        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "test.mkv"
            vid.write_text("dummy")
            result = probe_media(str(vid))
        assert result["video_streams"] == 1
        assert result["audio_streams"] == 1
        assert result["subtitle_streams"] == 1
        assert result["subtitle_languages"] == ["spa"]

    @patch("madrac.utils.media.subprocess.run")
    @patch("madrac.utils.media.resolve_executable")
    def test_ffprobe_failure(self, mock_resolve, mock_run):
        mock_resolve.return_value = "ffprobe"
        mock_run.return_value = MagicMock(returncode=1)
        result = probe_media("test.mkv")
        assert result["subtitle_streams"] == 0


class TestDemuxSubtitles:
    @patch("madrac.utils.media.detect_subtitle_tracks")
    @patch("madrac.utils.media.extract_subtitle_track")
    def test_demux_success(self, mock_extract, mock_detect):
        mock_detect.return_value = [
            {"index": 0, "codec": "srt", "language": "eng"},
            {"index": 1, "codec": "srt", "language": "spa"},
        ]
        mock_extract.side_effect = [True, True]

        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "test.mp4"
            vid.write_text("video")
            result = demux_subtitles(str(vid), output_dir=tmp)
            assert len(result) == 2
            assert all(p.endswith(".srt") for p in result)

    @patch("madrac.utils.media.detect_subtitle_tracks")
    def test_demux_no_tracks(self, mock_detect):
        mock_detect.return_value = []
        result = demux_subtitles("test.mp4")
        assert result == []

    @patch("madrac.utils.media.detect_subtitle_tracks")
    @patch("madrac.utils.media.extract_subtitle_track")
    def test_demux_partial_failure(self, mock_extract, mock_detect):
        mock_detect.return_value = [
            {"index": 0, "codec": "srt", "language": "eng"},
            {"index": 1, "codec": "srt", "language": "spa"},
        ]
        mock_extract.side_effect = [True, False]

        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "test.mp4"
            vid.write_text("video")
            result = demux_subtitles(str(vid), output_dir=tmp)
            assert len(result) == 1


class TestStripSubtitles:
    @patch("madrac.utils.media.resolve_executable")
    @patch("madrac.utils.media._srun")
    def test_strip_success(self, mock_run, mock_resolve):
        mock_resolve.return_value = "ffmpeg"
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "test.mp4"
            vid.write_text("video")
            out = strip_subtitles(str(vid))
            assert out.endswith("_clean.mp4")

    def test_strip_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="Video not found"):
            strip_subtitles("nonexistent.mp4")

    @patch("madrac.utils.media.resolve_executable")
    @patch("madrac.utils.media._srun")
    def test_strip_ffmpeg_failure(self, mock_run, mock_resolve):
        mock_resolve.return_value = "ffmpeg"
        mock_run.return_value = MagicMock(returncode=1, stderr="error")

        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "test.mp4"
            vid.write_text("video")
            with pytest.raises(RuntimeError, match="ffmpeg strip failed"):
                strip_subtitles(str(vid))

    @patch("madrac.utils.media.resolve_executable")
    @patch("madrac.utils.media._srun")
    def test_strip_custom_output(self, mock_run, mock_resolve):
        mock_resolve.return_value = "ffmpeg"
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "test.mp4"
            vid.write_text("video")
            out_path = str(Path(tmp) / "stripped.mp4")
            result = strip_subtitles(str(vid), output_path=out_path)
            assert result == out_path


class TestMuxStage:
    def get_stage(self):
        return MuxStage()

    def test_name(self):
        assert self.get_stage().name == "mux"

    @patch("madrac.pipeline.stages.mux.get_config")
    def test_disabled(self, mock_cfg):
        mock_cfg.return_value = False
        result = self.get_stage().execute("id", {}, MagicMock(), MagicMock(), lambda: False)
        assert result.success
        assert result.data == {"muxed": False}

    @patch("madrac.pipeline.stages.mux.get_config")
    def test_no_subtitle_path(self, mock_cfg):
        mock_cfg.return_value = True
        result = self.get_stage().execute("id", {"ruta": "/tmp/test.mp4"}, MagicMock(), MagicMock(), lambda: False)
        assert not result.success
        assert "subtitle" in result.error.lower()

    @patch("madrac.pipeline.stages.mux.get_config")
    def test_no_video_path(self, mock_cfg):
        mock_cfg.return_value = True
        result = self.get_stage().execute("id", {"subtitle_path": "/tmp/test.srt"}, MagicMock(), MagicMock(), lambda: False)
        assert not result.success
        assert "video" in result.error.lower()

    @patch("madrac.pipeline.stages.mux.get_config")
    def test_video_not_found(self, mock_cfg):
        mock_cfg.return_value = True
        ctx = {"subtitle_path": "/tmp/test.srt", "ruta": "/nonexistent.mp4"}
        result = self.get_stage().execute("id", ctx, MagicMock(), MagicMock(), lambda: False)
        assert not result.success

    @patch("madrac.pipeline.stages.mux.get_config")
    @patch("madrac.pipeline.stages.mux.mux_subtitles")
    def test_rollback_removes_file(self, mock_mux, mock_cfg):
        mock_cfg.return_value = True
        mock_mux.return_value = "/tmp/muxed.mp4"

        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "test.mp4"
            vid.write_text("video")
            srt = Path(tmp) / "test.srt"
            srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nhello")
            ctx = {"subtitle_path": str(srt), "ruta": str(vid)}
            result = self.get_stage().execute("id", ctx, MagicMock(), MagicMock(), lambda: False)
            assert result.success

            muxed_path = Path(tmp) / "muxed.mp4"
            muxed_path.write_text("muxed_video")
            ctx["muxed_path"] = str(muxed_path)
            self.get_stage().rollback(ctx)
            assert not muxed_path.exists()

    @patch("madrac.pipeline.stages.mux.get_config")
    def test_rollback_no_muxed_path(self, mock_cfg):
        mock_cfg.return_value = True
        self.get_stage().rollback({})
