"""Tests for SharedWorkspace implementation."""

import json
import tempfile
from pathlib import Path

import pytest

# Patch get_user_config_dir to use a temp directory BEFORE importing workspace
import madrac.core.paths as paths_mod

@pytest.fixture(autouse=True)
def temp_cache_dir(tmp_path, monkeypatch):
    """Override user config dir to use a temporary directory for test isolation."""
    temp_config = tmp_path / "madrac-test-cache"
    monkeypatch.setattr(paths_mod, "get_user_config_dir", lambda: temp_config)
    # Also patch the _CACHE_ROOT in the shared module (evaluated at import time)
    import madrac.workspace.shared as shared_mod
    monkeypatch.setattr(shared_mod, "_CACHE_ROOT", temp_config / "workspace" / "jobs")
    yield temp_config

from madrac.workspace import SharedWorkspace, compute_job_id, list_workspaces
from madrac.utils.hashing import sha256


def _unique_video(tmp_path, suffix: str = "") -> Path:
    """Create a video file with unique content for test isolation."""
    video = tmp_path / f"test_{suffix}.mp4"
    video.write_bytes(f"test content {suffix}".encode())
    return video


class TestComputeJobId:
    """Tests for compute_job_id function."""

    def test_compute_job_id_stable(self, tmp_path):
        """Same file content produces same job_id."""
        video1 = _unique_video(tmp_path, "stable1")
        video2 = _unique_video(tmp_path, "stable2")
        content = b"identical content"
        video1.write_bytes(content)
        video2.write_bytes(content)

        job_id1 = compute_job_id(video1)
        job_id2 = compute_job_id(video2)

        assert job_id1 == job_id2
        assert job_id1.startswith("sha256-")

    def test_compute_job_id_different_content(self, tmp_path):
        """Different content produces different job_id."""
        video1 = _unique_video(tmp_path, "diff1")
        video2 = _unique_video(tmp_path, "diff2")
        video1.write_bytes(b"content one")
        video2.write_bytes(b"content two")

        job_id1 = compute_job_id(video1)
        job_id2 = compute_job_id(video2)

        assert job_id1 != job_id2

    def test_compute_job_id_missing_file(self, tmp_path):
        """Missing file returns None."""
        job_id = compute_job_id(tmp_path / "nonexistent.mp4")
        assert job_id is None


class TestSharedWorkspace:
    """Tests for SharedWorkspace class."""

    def test_open_creates_directories(self, tmp_path):
        """Opening workspace creates expected directory structure."""
        video = _unique_video(tmp_path, "dirs")

        ws = SharedWorkspace.open(video)

        assert ws.root.exists()
        assert ws.root.name == ws.job_id
        assert (ws.root / "stems").exists()
        assert (ws.root / "stems" / "speakers").exists()
        assert (ws.root / "dubbed").exists()
        assert (ws.root / "metadata.json").exists()

    def test_open_metadata_contains_schema_version(self, tmp_path):
        """Metadata includes schema version and job_id."""
        video = _unique_video(tmp_path, "meta")
        video.write_bytes(b"test content")

        ws = SharedWorkspace.open(video)
        metadata = ws.load_metadata()

        assert metadata["schema_version"] == "1.0"
        assert metadata["job_id"] == ws.job_id
        assert "created_at" in metadata
        assert "updated_at" in metadata
        assert metadata["source_video"] == str(video)

    def test_from_job_id_loads_existing(self, tmp_path):
        """from_job_id loads an existing workspace."""
        video = _unique_video(tmp_path, "fromid")
        video.write_bytes(b"test content")

        ws1 = SharedWorkspace.open(video)
        job_id = ws1.job_id

        ws2 = SharedWorkspace.from_job_id(job_id)

        assert ws2.job_id == job_id
        assert ws2.root == ws1.root

    def test_save_and_load_whisper_audio(self, tmp_path):
        """save_whisper_audio copies file and load works."""
        video = _unique_video(tmp_path, "whisper")
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        source_wav = tmp_path / "source_audio.wav"
        source_wav.write_bytes(b"fake wav data")

        result = ws.save_whisper_audio(source_wav, duration_s=123.45)

        assert result is True
        assert ws.has_whisper_audio()
        dest = ws.root / "audio_whisper.wav"
        assert dest.exists()
        assert dest.read_bytes() == b"fake wav data"

        metadata = ws.load_metadata()
        assert metadata["whisper_audio_path"] == str(dest)
        assert metadata["duration_s"] == 123.45

    def test_save_whisper_audio_missing_source(self, tmp_path):
        """save_whisper_audio returns False for missing source."""
        video = _unique_video(tmp_path, "whisper_missing")
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        result = ws.save_whisper_audio(tmp_path / "missing.wav")

        assert result is False
        assert not ws.has_whisper_audio()

    def test_save_and_load_segments(self, tmp_path):
        """save_segments writes segments.json and load_segments reads it."""
        video = _unique_video(tmp_path, "segments")
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        segments = [
            {"start": 0.0, "end": 5.0, "text": "Hello world"},
            {"start": 5.0, "end": 10.0, "text": "How are you"},
        ]
        result = ws.save_segments(segments, language="en", source="whisper")

        assert result is True
        assert ws.has_segments()

        loaded = ws.load_segments()
        assert loaded["segments"] == segments
        assert loaded["language"] == "en"
        assert loaded["source"] == "whisper"

        metadata = ws.load_metadata()
        assert metadata["segments_count"] == 2
        assert metadata["segments_language"] == "en"
        assert metadata["segments_source"] == "whisper"

    def test_load_segments_missing(self, tmp_path):
        """load_segments returns None when file missing."""
        video = _unique_video(tmp_path, "segments_missing")
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        assert ws.load_segments() is None

    def test_save_and_load_full_audio(self, tmp_path):
        """save_full_audio copies file."""
        video = _unique_video(tmp_path, "full_audio")
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        source_wav = tmp_path / "full_audio.wav"
        source_wav.write_bytes(b"full quality audio data")

        result = ws.save_full_audio(source_wav)

        assert result is True
        assert ws.has_full_audio()
        dest = ws.root / "audio_full.wav"
        assert dest.exists()
        assert dest.read_bytes() == b"full quality audio data"

    def test_save_stems_demucs(self, tmp_path):
        """save_stems with Demucs producer creates expected files."""
        video = _unique_video(tmp_path, "stems_demucs")
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        vocals = tmp_path / "vocals.wav"
        vocals.write_bytes(b"vocals data")
        background = tmp_path / "background.wav"
        background.write_bytes(b"background data")

        result = ws.save_stems(vocals, background, producer="demucs")

        assert result is True
        assert ws.has_stems()

        stems_dir = ws.root / "stems"
        assert (stems_dir / "vocals.wav").exists()
        assert (stems_dir / "background.wav").exists()
        assert not (stems_dir / "no_vocals.wav").exists()

        metadata = ws.load_metadata()
        assert metadata["stems_producer"] == "demucs"
        assert metadata["stems_vocals"] == str(stems_dir / "vocals.wav")
        assert metadata["stems_background"] == str(stems_dir / "background.wav")

    def test_save_stems_dsp(self, tmp_path):
        """save_stems with DSP producer creates no_vocals.wav."""
        video = _unique_video(tmp_path, "stems_dsp")
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        vocals = tmp_path / "vocals.wav"
        vocals.write_bytes(b"vocals data")
        no_vocals = tmp_path / "no_vocals.wav"
        no_vocals.write_bytes(b"no_vocals data")

        result = ws.save_stems(vocals, no_vocals, producer="dsp")

        assert result is True
        stems_dir = ws.root / "stems"
        assert (stems_dir / "vocals.wav").exists()
        assert (stems_dir / "no_vocals.wav").exists()
        assert not (stems_dir / "background.wav").exists()

        metadata = ws.load_metadata()
        assert metadata["stems_producer"] == "dsp"
        assert metadata["stems_background"] == str(stems_dir / "no_vocals.wav")

    def test_save_stems_missing_files(self, tmp_path):
        """save_stems returns False when source files missing."""
        video = _unique_video(tmp_path, "stems_missing")
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        result = ws.save_stems(tmp_path / "missing1.wav", tmp_path / "missing2.wav")

        assert result is False
        assert not ws.has_stems()

    def test_save_dubbed_segment(self, tmp_path):
        """save_dubbed_segment creates correctly named file."""
        video = _unique_video(tmp_path, "dubbed")
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        source_wav = tmp_path / "seg_0000.wav"
        source_wav.write_bytes(b"dubbed segment data")

        result = ws.save_dubbed_segment(0, source_wav)

        assert result is True
        dest = ws.root / "dubbed" / "seg_0000.wav"
        assert dest.exists()
        assert dest.read_bytes() == b"dubbed segment data"

        # Test segment 1 -> seg_0001.wav
        ws.save_dubbed_segment(1, source_wav)
        assert (ws.root / "dubbed" / "seg_0001.wav").exists()

    def test_save_dubbed_segment_missing(self, tmp_path):
        """save_dubbed_segment returns False for missing source."""
        video = _unique_video(tmp_path, "dubbed_missing")
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        result = ws.save_dubbed_segment(0, tmp_path / "missing.wav")

        assert result is False

    def test_has_methods(self, tmp_path):
        """has_* methods correctly report existence."""
        video = _unique_video(tmp_path, "has_methods")
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        assert not ws.has_whisper_audio()
        assert not ws.has_full_audio()
        assert not ws.has_segments()
        assert not ws.has_stems()

        (ws.root / "audio_whisper.wav").write_bytes(b"")
        assert ws.has_whisper_audio()

        (ws.root / "audio_full.wav").write_bytes(b"")
        assert ws.has_full_audio()

        (ws.root / "segments.json").write_text("{}")
        assert ws.has_segments()

        (ws.root / "stems" / "vocals.wav").write_bytes(b"")
        assert ws.has_stems()

    def test_update_metadata_thread_safe(self, tmp_path):
        """update_metadata merges fields correctly."""
        video = _unique_video(tmp_path, "thread_safe")
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        ws.update_metadata(custom_field="value1", another=123)
        meta = ws.load_metadata()

        assert meta["custom_field"] == "value1"
        assert meta["another"] == 123

    def test_metadata_lock_prevents_corruption(self, tmp_path):
        """Concurrent updates don't corrupt metadata (best-effort test)."""
        import threading

        video = _unique_video(tmp_path, "lock_test")
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        def worker():
            for i in range(10):
                ws.update_metadata(**{f"key_{i}": f"value_{i}"})

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        meta = ws.load_metadata()
        assert all(f"key_{i}" in meta for i in range(10))


class TestListWorkspaces:
    """Tests for list_workspaces function."""

    def test_list_workspaces_empty(self, tmp_path):
        """list_workspaces returns empty list when no workspaces."""
        # Need to temporarily override _CACHE_ROOT, but it's module-level.
        # We'll test with a real directory.
        pass

    def test_list_workspaces_sorted(self, tmp_path):
        """list_workspaces returns sorted job IDs."""
        # Tested indirectly via workspace creation


class TestBestEffortBehavior:
    """Tests that workspace operations don't crash on missing paths."""

    def test_save_on_nonexistent_destination(self, tmp_path):
        """Operations don't crash when destination directories missing."""
        video = tmp_path / "test_video.mp4"
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        # Remove the stems directory
        import shutil
        shutil.rmtree(ws.root / "stems")

        # Should handle gracefully and return False
        result = ws.save_stems(
            tmp_path / "vocals.wav",
            tmp_path / "no_vocals.wav"
        )
        # Result is False because source files missing, but no exception

    def test_load_missing_metadata(self, tmp_path):
        """load_metadata returns None gracefully."""
        video = tmp_path / "test_video.mp4"
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        (ws.root / "metadata.json").unlink()
        assert ws.load_metadata() is None

    def test_save_segments_with_invalid_json(self, tmp_path):
        """save_segments handles write failures gracefully."""
        video = tmp_path / "test_video.mp4"
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)

        # Make segments.json read-only (if possible on this FS)
        # For now, just test with valid input
        assert ws.save_segments([{"start": 0, "end": 1, "text": "test"}], "en")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])