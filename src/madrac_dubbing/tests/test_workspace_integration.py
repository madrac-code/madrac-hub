"""Tests for SharedWorkspace integration in dubbing pipeline."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from madrac_dubbing.pipeline.models import (
    DubbingJob, DubbingConfig, DubbingStatus, Segment
)
from madrac_dubbing.pipeline.dubbing_pipeline import DubbingPipeline


def _mock_segments():
    """Return mock Segment objects (as parse_srt_file would)."""
    return [Segment(index=1, start_ms=0, end_ms=5000, text="Hello")]


def _make_pipeline():
    """Create a DubbingPipeline with a mocked TTS engine."""
    pipeline = DubbingPipeline()
    mock_tts = MagicMock()
    mock_tts.synthesize.return_value = []  # no TTS segments needed for these tests
    mock_tts.cache_stats = Mock(hits=0, misses=0, hit_rate=0.0)
    pipeline.tts_engine = mock_tts
    return pipeline, mock_tts


def _make_job(tmp_path, video_content=b"fake video content"):
    """Create a test DubbingJob with temporary paths."""
    video_path = tmp_path / "test_video.mp4"
    srt_path = tmp_path / "test.srt"
    output_path = tmp_path / "output.mkv"

    video_path.write_bytes(video_content)
    srt_path.write_text("1\n00:00:00,000 --> 00:00:05,000\nHello\n")

    config = DubbingConfig(language='es', high_quality=True)
    return DubbingJob(
        job_id='test-workspace-1',
        video_path=video_path,
        srt_path=srt_path,
        output_path=output_path,
        config=config
    )


class TestWorkspaceIntegration:
    """Tests for SharedWorkspace read-side integration in DUBS pipeline."""

    def test_workspace_not_available_continues_normally(self, tmp_path):
        """When SharedWorkspace import fails, pipeline should continue normally."""
        job = _make_job(tmp_path)
        pipeline, _mock_tts = _make_pipeline()

        with patch('madrac_dubbing.pipeline.dubbing_pipeline._WORKSPACE_AVAILABLE', False):
            with patch('madrac_dubbing.pipeline.dubbing_pipeline.extract_audio') as mock_extract:
                with patch('madrac_dubbing.pipeline.dubbing_pipeline.parse_srt_file') as mock_parse:
                    with patch('madrac_dubbing.pipeline.dubbing_pipeline.has_demucs', return_value=False):
                        with patch('madrac_dubbing.audio.mixer.reduce_vocals') as mock_reduce:
                            with patch('madrac_dubbing.pipeline.dubbing_pipeline.sf') as mock_sf:
                                with patch('madrac_dubbing.pipeline.dubbing_pipeline.sync_tts_to_subtitle') as mock_sync:
                                    with patch('madrac_dubbing.pipeline.dubbing_pipeline.normalize_loudness') as mock_norm:
                                        with patch('madrac_dubbing.pipeline.dubbing_pipeline.mix_audio_tracks') as mock_mix:
                                            with patch('madrac_dubbing.pipeline.dubbing_pipeline.mux_audio_to_video') as mock_mux:
                                                mock_parse.return_value = _mock_segments()
                                                mock_sf.read.return_value = ([], 16000)
                                                mock_reduce.return_value = ([], 16000)
                                                mock_sync.return_value = ([], 16000, Mock())
                                                mock_norm.return_value = []
                                                mock_mix.return_value = []

                                                result = pipeline.process(job)

                                                assert result is True
                                                mock_extract.assert_called_once()

    def test_workspace_has_stems_skips_extraction_and_demucs(self, tmp_path):
        """When workspace has cached stems, skip both extraction and Demucs."""
        job = _make_job(tmp_path)
        pipeline, _mock_tts = _make_pipeline()

        with patch('madrac_dubbing.pipeline.dubbing_pipeline._WORKSPACE_AVAILABLE', True):
            with patch('madrac_dubbing.pipeline.dubbing_pipeline.compute_job_id',
                       return_value="sha256-testhash", create=True) as mock_compute_id:
                with patch('madrac_dubbing.pipeline.dubbing_pipeline.SharedWorkspace',
                           create=True) as mock_ws_class:
                    with patch('madrac_dubbing.pipeline.dubbing_pipeline.extract_audio') as mock_extract:
                        with patch('madrac_dubbing.pipeline.dubbing_pipeline.parse_srt_file') as mock_parse:
                            with patch('madrac_dubbing.pipeline.dubbing_pipeline.separate_stems') as mock_separate:
                                with patch('madrac_dubbing.pipeline.dubbing_pipeline.sf') as mock_sf:
                                    with patch('madrac_dubbing.pipeline.dubbing_pipeline.sync_tts_to_subtitle') as mock_sync:
                                        with patch('madrac_dubbing.pipeline.dubbing_pipeline.normalize_loudness') as mock_norm:
                                            with patch('madrac_dubbing.pipeline.dubbing_pipeline.mix_audio_tracks') as mock_mix:
                                                with patch('madrac_dubbing.pipeline.dubbing_pipeline.mux_audio_to_video') as mock_mux:
                                                    stems_dir = tmp_path / "ws" / "sha256-testhash" / "stems"
                                                    stems_dir.mkdir(parents=True)
                                                    (stems_dir / "background.wav").write_bytes(b"bg")

                                                    mock_ws = MagicMock()
                                                    mock_ws.has_stems.return_value = True
                                                    mock_ws.root = tmp_path / "ws" / "sha256-testhash"
                                                    mock_ws.load_metadata.return_value = {
                                                        "stems_producer": "demucs",
                                                        "stems_model": "htdemucs"
                                                    }
                                                    mock_ws_class.from_job_id.return_value = mock_ws

                                                    mock_parse.return_value = _mock_segments()
                                                    mock_sf.read.return_value = ([], 16000)
                                                    mock_sync.return_value = ([], 16000, Mock())
                                                    mock_norm.return_value = []
                                                    mock_mix.return_value = []

                                                    result = pipeline.process(job)

                                                    assert result is True
                                                    mock_compute_id.assert_called_once_with(job.video_path)
                                                    mock_ws_class.from_job_id.assert_called_once_with("sha256-testhash")
                                                    mock_ws.has_stems.assert_called_once()
                                                    # Extraction AND Demucs skipped
                                                    mock_extract.assert_not_called()
                                                    mock_separate.assert_not_called()
                                                    # Background read from workspace stems
                                                    bg_arg = mock_sf.read.call_args[0][0]
                                                    assert "background.wav" in str(bg_arg)

    def test_workspace_no_stems_extracts_fresh_audio(self, tmp_path):
        """When workspace exists but has no stems, extract fresh audio and run Demucs."""
        job = _make_job(tmp_path)
        pipeline, _mock_tts = _make_pipeline()

        with patch('madrac_dubbing.pipeline.dubbing_pipeline._WORKSPACE_AVAILABLE', True):
            with patch('madrac_dubbing.pipeline.dubbing_pipeline.compute_job_id',
                       return_value="sha256-testhash", create=True) as mock_compute_id:
                with patch('madrac_dubbing.pipeline.dubbing_pipeline.SharedWorkspace',
                           create=True) as mock_ws_class:
                    with patch('madrac_dubbing.pipeline.dubbing_pipeline.extract_audio') as mock_extract:
                        with patch('madrac_dubbing.pipeline.dubbing_pipeline.parse_srt_file') as mock_parse:
                            with patch('madrac_dubbing.pipeline.dubbing_pipeline.separate_stems') as mock_separate:
                                with patch('madrac_dubbing.pipeline.dubbing_pipeline.has_demucs', return_value=True):
                                    with patch('madrac_dubbing.pipeline.dubbing_pipeline.hash_video') as mock_hash:
                                        with patch('madrac_dubbing.pipeline.dubbing_pipeline.sf') as mock_sf:
                                            with patch('madrac_dubbing.pipeline.dubbing_pipeline.sync_tts_to_subtitle') as mock_sync:
                                                with patch('madrac_dubbing.pipeline.dubbing_pipeline.normalize_loudness') as mock_norm:
                                                    with patch('madrac_dubbing.pipeline.dubbing_pipeline.mix_audio_tracks') as mock_mix:
                                                        with patch('madrac_dubbing.pipeline.dubbing_pipeline.mux_audio_to_video') as mock_mux:
                                                            mock_ws = MagicMock()
                                                            mock_ws.has_stems.return_value = False
                                                            mock_ws_class.from_job_id.return_value = mock_ws

                                                            mock_parse.return_value = _mock_segments()
                                                            mock_hash.return_value = "videohash"
                                                            mock_separate.return_value = MagicMock(
                                                                background=tmp_path / "bg.wav",
                                                                vocals=tmp_path / "vocals.wav",
                                                                metadata={"cache_hit": False, "model": "htdemucs"}
                                                            )
                                                            mock_sf.read.return_value = ([], 16000)
                                                            mock_sync.return_value = ([], 16000, Mock())
                                                            mock_norm.return_value = []
                                                            mock_mix.return_value = []

                                                            result = pipeline.process(job)

                                                            assert result is True
                                                            mock_extract.assert_called_once()
                                                            mock_separate.assert_called_once()
                                                            # Stems saved to workspace after Demucs
                                                            mock_ws.save_stems.assert_called_once()

    def test_workspace_import_error_handled_gracefully(self, tmp_path):
        """When SharedWorkspace import raises ImportError, pipeline continues."""
        job = _make_job(tmp_path)
        pipeline, _mock_tts = _make_pipeline()

        with patch('madrac_dubbing.pipeline.dubbing_pipeline._WORKSPACE_AVAILABLE', False):
            with patch('madrac_dubbing.pipeline.dubbing_pipeline.extract_audio') as mock_extract:
                with patch('madrac_dubbing.pipeline.dubbing_pipeline.parse_srt_file') as mock_parse:
                    with patch('madrac_dubbing.pipeline.dubbing_pipeline.has_demucs', return_value=False):
                        with patch('madrac_dubbing.audio.mixer.reduce_vocals') as mock_reduce:
                            with patch('madrac_dubbing.pipeline.dubbing_pipeline.sf') as mock_sf:
                                with patch('madrac_dubbing.pipeline.dubbing_pipeline.sync_tts_to_subtitle') as mock_sync:
                                    with patch('madrac_dubbing.pipeline.dubbing_pipeline.normalize_loudness') as mock_norm:
                                        with patch('madrac_dubbing.pipeline.dubbing_pipeline.mix_audio_tracks') as mock_mix:
                                            with patch('madrac_dubbing.pipeline.dubbing_pipeline.mux_audio_to_video') as mock_mux:
                                                mock_parse.return_value = _mock_segments()
                                                mock_sf.read.return_value = ([], 16000)
                                                mock_reduce.return_value = ([], 16000)
                                                mock_sync.return_value = ([], 16000, Mock())
                                                mock_norm.return_value = []
                                                mock_mix.return_value = []

                                                result = pipeline.process(job)

                                                assert result is True
                                                mock_extract.assert_called_once()

    def test_workspace_runtime_error_handled_gracefully(self, tmp_path):
        """When workspace operations raise runtime error, pipeline falls back."""
        job = _make_job(tmp_path)
        pipeline, _mock_tts = _make_pipeline()

        with patch('madrac_dubbing.pipeline.dubbing_pipeline._WORKSPACE_AVAILABLE', True):
            with patch('madrac_dubbing.pipeline.dubbing_pipeline.compute_job_id',
                       return_value="sha256-testhash", create=True) as mock_compute_id:
                with patch('madrac_dubbing.pipeline.dubbing_pipeline.SharedWorkspace',
                           create=True) as mock_ws_class:
                    with patch('madrac_dubbing.pipeline.dubbing_pipeline.extract_audio') as mock_extract:
                        with patch('madrac_dubbing.pipeline.dubbing_pipeline.parse_srt_file') as mock_parse:
                            with patch('madrac_dubbing.pipeline.dubbing_pipeline.has_demucs', return_value=False):
                                with patch('madrac_dubbing.audio.mixer.reduce_vocals') as mock_reduce:
                                    with patch('madrac_dubbing.pipeline.dubbing_pipeline.sf') as mock_sf:
                                        with patch('madrac_dubbing.pipeline.dubbing_pipeline.sync_tts_to_subtitle') as mock_sync:
                                            with patch('madrac_dubbing.pipeline.dubbing_pipeline.normalize_loudness') as mock_norm:
                                                with patch('madrac_dubbing.pipeline.dubbing_pipeline.mix_audio_tracks') as mock_mix:
                                                    with patch('madrac_dubbing.pipeline.dubbing_pipeline.mux_audio_to_video') as mock_mux:
                                                        # Workspace throws error â†’ fallback to normal flow
                                                        mock_ws_class.from_job_id.side_effect = Exception("Cache corrupt")

                                                        mock_parse.return_value = _mock_segments()
                                                        mock_sf.read.return_value = ([], 16000)
                                                        mock_reduce.return_value = ([], 16000)
                                                        mock_sync.return_value = ([], 16000, Mock())
                                                        mock_norm.return_value = []
                                                        mock_mix.return_value = []

                                                        result = pipeline.process(job)

                                                        assert result is True
                                                        mock_extract.assert_called_once()


class TestWorkspacePriority:
    """Tests verifying the optimization priority order."""

    def test_stems_cached_priority_over_whisper_audio(self, tmp_path):
        """Stems cache hit should skip both extraction and Demucs."""
        job = _make_job(tmp_path)
        pipeline, _mock_tts = _make_pipeline()

        with patch('madrac_dubbing.pipeline.dubbing_pipeline._WORKSPACE_AVAILABLE', True):
            with patch('madrac_dubbing.pipeline.dubbing_pipeline.compute_job_id',
                       return_value="sha256-testhash", create=True):
                with patch('madrac_dubbing.pipeline.dubbing_pipeline.SharedWorkspace',
                           create=True) as mock_ws_class:
                    with patch('madrac_dubbing.pipeline.dubbing_pipeline.extract_audio') as mock_extract:
                        with patch('madrac_dubbing.pipeline.dubbing_pipeline.parse_srt_file') as mock_parse:
                            with patch('madrac_dubbing.pipeline.dubbing_pipeline.separate_stems') as mock_separate:
                                with patch('madrac_dubbing.pipeline.dubbing_pipeline.sf') as mock_sf:
                                    with patch('madrac_dubbing.pipeline.dubbing_pipeline.sync_tts_to_subtitle') as mock_sync:
                                        with patch('madrac_dubbing.pipeline.dubbing_pipeline.normalize_loudness') as mock_norm:
                                            with patch('madrac_dubbing.pipeline.dubbing_pipeline.mix_audio_tracks') as mock_mix:
                                                with patch('madrac_dubbing.pipeline.dubbing_pipeline.mux_audio_to_video') as mock_mux:
                                                    stems_dir = tmp_path / "ws2" / "sha256-testhash" / "stems"
                                                    stems_dir.mkdir(parents=True)
                                                    (stems_dir / "background.wav").write_bytes(b"bg")

                                                    mock_ws = MagicMock()
                                                    mock_ws.has_stems.return_value = True
                                                    mock_ws.root = tmp_path / "ws2" / "sha256-testhash"
                                                    mock_ws.load_metadata.return_value = {
                                                        "stems_producer": "demucs",
                                                        "stems_model": "htdemucs"
                                                    }
                                                    mock_ws_class.from_job_id.return_value = mock_ws

                                                    mock_parse.return_value = _mock_segments()
                                                    mock_sf.read.return_value = ([], 16000)
                                                    mock_sync.return_value = ([], 16000, Mock())
                                                    mock_norm.return_value = []
                                                    mock_mix.return_value = []

                                                    result = pipeline.process(job)

                                                    assert result is True
                                                    mock_extract.assert_not_called()
                                                    mock_separate.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
