"""RECON Phase 1 tests — diarization contract, paths, metadata (mocked model).

The heavy model (resemblyzer VoiceEncoder) is mocked; clustering with
scikit-learn runs for real. Integration against a real model is covered
by manual/E2E runs, not CI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

# madrac_recon lives at the monorepo src/ root (sibling of madrac_subs).
_SRC_ROOT = Path(__file__).resolve().parents[2]
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

import madrac.workspace.shared as shared_mod
from madrac.workspace import SharedWorkspace


@pytest.fixture(autouse=True)
def temp_workspace_root(tmp_path, monkeypatch):
    root = tmp_path / "workspace" / "jobs"
    monkeypatch.setattr(shared_mod, "_CACHE_ROOT", root)
    return root


def _make_job(tmp_path: Path, with_audio: bool = True) -> SharedWorkspace:
    """Create a real workspace with metadata.json and (optionally) audio."""
    video = tmp_path / "test.mp4"
    video.write_bytes(b"unique video content for recon")
    ws = SharedWorkspace.open(video)
    if with_audio:
        import soundfile as sf

        samples = (np.zeros(8 * 16000)).astype(np.int16)
        audio = tmp_path / "audio_whisper.wav"
        sf.write(str(audio), samples, 16000)
        ws.save_whisper_audio(audio, duration_s=8.0)
    return ws


def _fake_embeds(wav: np.ndarray) -> np.ndarray:
    """Two clear speaker clusters in embedding space (no model needed)."""
    window = int(1.6 * 16000)
    hop = int(0.5 * 16000)
    n = (len(wav) - window) // hop + 1
    embeds = np.zeros((n, 256))
    half = n // 2
    embeds[:half, 0] = 1.0
    embeds[half:, 1] = 1.0
    return embeds


@pytest.fixture(autouse=True)
def mock_encoder(monkeypatch):
    from madrac_recon import diarize as diarize_mod

    monkeypatch.setattr(diarize_mod, "_embed_frames", _fake_embeds)


class TestDiarizeErrors:
    def test_diarize_job_missing_workspace_raises(self, tmp_path):
        from madrac_recon import diarize_job

        with pytest.raises(ValueError, match="Workspace sha256-.* not found"):
            diarize_job("sha256-1234567890abcdef")

    def test_diarize_job_missing_audio_raises(self, tmp_path):
        from madrac_recon import diarize_job

        ws = _make_job(tmp_path, with_audio=False)
        with pytest.raises(ValueError, match="No audio"):
            diarize_job(ws.job_id)

    def test_diarize_video_without_workspace_raises(self, tmp_path):
        from madrac_recon import diarize_video

        video = tmp_path / "nuevo.mp4"
        video.write_bytes(b"content")
        with pytest.raises(ValueError, match="not found"):
            diarize_video(str(video))


class TestDiarizeContract:
    def test_persists_speaker_wavs_json_and_metadata(self, tmp_path):
        from madrac_recon import diarize_job

        ws = _make_job(tmp_path)
        summary = diarize_job(ws.job_id)

        assert summary["status"] == "done"
        assert summary["job_id"] == ws.job_id
        assert summary["speaker_count"] == 2
        assert summary["diarizer"] == "resemblyzer"
        assert summary["sample_rate"] == 16000

        wavs = sorted(p.name for p in ws.speakers_dir.glob("speaker_*.wav"))
        assert wavs == ["speaker_0.wav", "speaker_1.wav"]
        for p in summary["speaker_paths"]:
            assert Path(p).exists()

        speakers = json.loads((ws.root / "speakers.json").read_text(encoding="utf-8"))
        assert speakers["schema_version"] == "1.0"
        assert speakers["speaker_count"] == 2
        assert len(speakers["speakers"]) == 2
        assert speakers["speakers"][0]["speaker_id"] == "speaker_0"
        assert speakers["speakers"][0]["name"] == "Speaker 1"
        assert all("segments" in s for s in speakers["speakers"])

        meta = ws.load_metadata()
        assert meta["artifacts"] == {"stems": {"speakers": True}}
        assert meta["speaker_count"] == 2
        assert meta["speakers_json_path"] == str(ws.root / "speakers.json")
        assert meta["diarizer"] == "resemblyzer"

        assert ws.has_speakers() is True

    def test_audio_full_preferred_over_whisper(self, tmp_path):
        from madrac_recon import diarize_job

        ws = _make_job(tmp_path)
        import soundfile as sf

        full = tmp_path / "audio_full.wav"
        sf.write(str(full), (np.zeros(8 * 16000)).astype(np.int16), 16000)
        ws.save_full_audio(full)
        summary = diarize_job(ws.job_id)
        assert summary["speaker_count"] == 2

    def test_single_speaker_when_max_speakers_1(self, tmp_path):
        from madrac_recon import diarize_job

        ws = _make_job(tmp_path)
        summary = diarize_job(ws.job_id, min_speakers=1, max_speakers=1)
        assert summary["speaker_count"] == 1


class TestDiarizeTool:
    @pytest.mark.asyncio
    async def test_requires_arg(self, tmp_path):
        from madrac.mcp.tools.recon import diarize_speakers

        tool = diarize_speakers({})
        result = await tool()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_rejects_both_args(self, tmp_path):
        from madrac.mcp.tools.recon import diarize_speakers

        tool = diarize_speakers({})
        result = await tool(job_id="x", video_path="y")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_diarize_by_job_id(self, tmp_path):
        from madrac.mcp.tools.recon import diarize_speakers

        ws = _make_job(tmp_path)
        tool = diarize_speakers({})
        result = await tool(job_id=ws.job_id)
        assert result["status"] == "done"
        assert result["speaker_count"] == 2

    @pytest.mark.asyncio
    async def test_error_surfaces_cleanly(self, tmp_path):
        from madrac.mcp.tools.recon import diarize_speakers

        tool = diarize_speakers({})
        result = await tool(job_id="sha256-0000000000000000")
        assert "error" in result