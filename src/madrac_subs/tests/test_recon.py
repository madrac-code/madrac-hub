"""RECON Phase 1 tests — diarization contract, paths, metadata (mocked model).

The heavy model (resemblyzer VoiceEncoder) is mocked; clustering with
scikit-learn runs for real. Integration against a real model is covered
by manual/E2E runs, not CI.
"""

from __future__ import annotations

import asyncio
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


def _pretrained_model_available() -> bool:
    """True when the real resemblyzer pretrained.pt is bundled in the venv."""
    try:
        import resemblyzer
    except ImportError:
        return False
    return (Path(resemblyzer.__file__).parent / "pretrained.pt").exists()


@pytest.mark.skipif(
    not _pretrained_model_available(),
    reason="resemblyzer pretrained.pt not present (run once with internet)",
)
def test_embed_frames_real_encoder_api(tmp_path):
    """Real VoiceEncoder smoke test: PyPI 0.1.4 has no embed_frames method."""
    from madrac_recon import diarize as recon

    samples = np.random.default_rng(0).uniform(-1, 1, 4 * 16000).astype(np.float32)
    embeds = recon._embed_frames(samples)
    assert embeds.ndim == 2
    assert embeds.shape[0] >= 1
    assert embeds.shape[1] == 256


class TestMapSegments:
    """Tests for RECON Phase 2: speaker-to-segment mapping."""

    def _make_diarization(self, ws: SharedWorkspace, turns: dict[str, list[tuple[float, float]]]) -> None:
        """Write speakers.json with given speaker turns."""
        speakers_data = {
            "schema_version": "1.0",
            "diarizer": "resemblyzer",
            "sample_rate": 16000,
            "source_audio": str(ws.root / "audio_whisper.wav"),
            "speaker_count": len(turns),
            "speakers": [
                {
                    "speaker_id": f"speaker_{i}",
                    "name": f"Speaker {i + 1}",
                    "segments": [{"start": s, "end": e} for s, e in spk_turns],
                }
                for i, spk_turns in enumerate(turns.values())
            ],
        }
        (ws.root / "speakers.json").write_text(json.dumps(speakers_data), encoding="utf-8")

    def _make_segments(self, ws: SharedWorkspace, segs: list[dict]) -> None:
        """Write segments.json with given segments."""
        (ws.root / "segments.json").write_text(
            json.dumps({"segments": segs, "language": "en", "source": "whisper"}),
            encoding="utf-8",
        )

    def test_map_segments_basic_overlap(self, tmp_path):
        """Segment fully inside one speaker turn -> assigned to that speaker with confidence 1.0."""
        from madrac_recon import map_job, map_speakers_to_segments
        from madrac.workspace import SharedWorkspace

        ws = _make_job(tmp_path)
        # Speaker 0: 0-10s, Speaker 1: 10-20s
        self._make_diarization(ws, {"spk0": [(0.0, 10.0)], "spk1": [(10.0, 20.0)]})
        # Segment 2-5s fully inside spk0
        self._make_segments(ws, [{"start": 2.0, "end": 5.0, "text": "hello"}])

        result = map_job(ws.job_id)

        assert result["status"] == "done"
        assert result["mapped_count"] == 1
        assert result["unmapped"] == 0
        assert result["total_confidence"] == 1.0

        mapped = json.loads((ws.root / "speaker_segments.json").read_text(encoding="utf-8"))
        assert mapped["segments"][0]["speaker_id"] == "speaker_0"
        assert mapped["segments"][0]["speaker_name"] == "Speaker 1"
        assert mapped["segments"][0]["confidence"] == 1.0
        assert mapped["segments"][0]["segment_index"] == 0

    def test_map_segments_max_overlap_picks_dominant(self, tmp_path):
        """Segment overlapping two speakers -> assigned to one with max total overlap."""
        from madrac_recon import map_job
        from madrac.workspace import SharedWorkspace

        ws = _make_job(tmp_path)
        # Speaker 0: 0-8s and 12-20s (total 16s in segment range)
        # Speaker 1: 8-12s (4s in segment range)
        # Segment 0-20s: overlap spk0=16s, spk1=4s -> spk0 wins
        self._make_diarization(ws, {"spk0": [(0.0, 8.0), (12.0, 20.0)], "spk1": [(8.0, 12.0)]})
        self._make_segments(ws, [{"start": 0.0, "end": 20.0, "text": "long"}])

        result = map_job(ws.job_id)
        assert result["total_confidence"] == 0.8  # 16/20

        mapped = json.loads((ws.root / "speaker_segments.json").read_text(encoding="utf-8"))
        assert mapped["segments"][0]["speaker_id"] == "speaker_0"
        assert mapped["segments"][0]["confidence"] == 0.8

    def test_map_segments_fallback_closest_when_no_overlap(self, tmp_path):
        """Segment in gap between turns -> fallback to closest speaker, confidence 0."""
        from madrac_recon import map_job
        from madrac.workspace import SharedWorkspace

        ws = _make_job(tmp_path)
        # Speaker 0: 0-5s, Speaker 1: 15-20s. Gap 5-15s.
        self._make_diarization(ws, {"spk0": [(0.0, 5.0)], "spk1": [(15.0, 20.0)]})
        # Segment in gap (7-10s) -> no overlap with either
        self._make_segments(ws, [{"start": 7.0, "end": 10.0, "text": "gap"}])

        result = map_job(ws.job_id)
        assert result["unmapped"] == 1
        assert result["total_confidence"] == 0.0

        mapped = json.loads((ws.root / "speaker_segments.json").read_text(encoding="utf-8"))
        # Center is 8.5, closest to spk1 (turn at 15) than spk0 (turn at 5)? Distance: 8.5-5=3.5 vs 15-8.5=6.5 -> spk0 is closer
        # Wait: distance_to_turns uses min distance to ANY boundary. spk0 boundaries: 0,5. spk1: 15,20.
        # Center 8.5: dist to 5 = 3.5, dist to 15 = 6.5 -> spk0 is closer
        assert mapped["segments"][0]["speaker_id"] == "speaker_0"
        assert mapped["segments"][0]["confidence"] == 0.0

    def test_map_segments_preserves_speaker_name(self, tmp_path):
        """Mapped segments carry speaker_name from speakers.json."""
        from madrac_recon import map_job
        from madrac.workspace import SharedWorkspace

        ws = _make_job(tmp_path)
        self._make_diarization(ws, {"spk0": [(0.0, 10.0)]})
        self._make_segments(ws, [{"start": 1.0, "end": 2.0, "text": "test"}])

        result = map_job(ws.job_id)
        mapped = json.loads((ws.root / "speaker_segments.json").read_text(encoding="utf-8"))
        assert mapped["segments"][0]["speaker_name"] == "Speaker 1"

    def test_map_segments_updates_metadata_artifacts(self, tmp_path):
        """After mapping, metadata.json shows speaker_segments artifact."""
        from madrac_recon import map_job
        from madrac.workspace import SharedWorkspace

        ws = _make_job(tmp_path)
        self._make_diarization(ws, {"spk0": [(0.0, 10.0)]})
        self._make_segments(ws, [{"start": 1.0, "end": 2.0, "text": "test"}])

        map_job(ws.job_id)

        meta = ws.load_metadata()
        assert meta["artifacts"]["stems"]["speaker_segments"] is True
        assert "speaker_segments_path" in meta
        assert meta["speaker_mapped_count"] == 1
        assert "speaker_mapping_confidence" in meta
        assert ws.has_speaker_segments() is True

    def test_map_job_missing_segments_raises(self, tmp_path):
        """Missing segments.json raises clear error."""
        from madrac_recon import map_job
        from madrac.workspace import SharedWorkspace

        ws = _make_job(tmp_path)
        self._make_diarization(ws, {"spk0": [(0.0, 10.0)]})
        # No segments.json

        with pytest.raises(ValueError, match="segments.json not found"):
            map_job(ws.job_id)

    def test_map_job_missing_speakers_raises(self, tmp_path):
        """Missing speakers.json raises clear error."""
        from madrac_recon import map_job
        from madrac.workspace import SharedWorkspace

        ws = _make_job(tmp_path)
        self._make_segments(ws, [{"start": 1.0, "end": 2.0, "text": "test"}])
        # No speakers.json

        with pytest.raises(ValueError, match="speakers.json not found"):
            map_job(ws.job_id)

    def test_map_job_multiple_segments_independent(self, tmp_path):
        """Each segment mapped independently; confidence averaged."""
        from madrac_recon import map_job
        from madrac.workspace import SharedWorkspace

        ws = _make_job(tmp_path)
        self._make_diarization(ws, {"spk0": [(0.0, 10.0)], "spk1": [(10.0, 20.0)]})
        self._make_segments(ws, [
            {"start": 1.0, "end": 2.0, "text": "a"},   # in spk0 -> conf 1.0
            {"start": 11.0, "end": 12.0, "text": "b"}, # in spk1 -> conf 1.0
        ])

        result = map_job(ws.job_id)
        assert result["mapped_count"] == 2
        assert result["total_confidence"] == 1.0

        mapped = json.loads((ws.root / "speaker_segments.json").read_text(encoding="utf-8"))
        assert mapped["segments"][0]["speaker_id"] == "speaker_0"
        assert mapped["segments"][1]["speaker_id"] == "speaker_1"

    @pytest.mark.asyncio
    async def test_map_speakers_tool_requires_job_id(self, tmp_path):
        """MCP tool rejects calls without job_id."""
        from madrac.mcp.tools.recon_map import map_speakers_to_segments

        tool = map_speakers_to_segments({})
        result = await tool()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_map_speakers_tool_ok(self, tmp_path):
        """MCP tool works with valid job_id."""
        from madrac.mcp.tools.recon_map import map_speakers_to_segments
        from madrac.workspace import SharedWorkspace

        ws = _make_job(tmp_path)
        self._make_diarization(ws, {"spk0": [(0.0, 10.0)]})
        self._make_segments(ws, [{"start": 1.0, "end": 2.0, "text": "test"}])

        tool = map_speakers_to_segments({})
        result = await tool(job_id=ws.job_id)

        assert result["status"] == "done"
        assert result["mapped_count"] == 1


class TestCharacterIdentity:
    """Tests for RECON Character Identity: speaker_id → character_id mapping."""

    def _make_speakers(self, ws: SharedWorkspace, speakers: list[dict]) -> None:
        """Write speakers.json with given speakers."""
        speakers_data = {
            "schema_version": "1.0",
            "diarizer": "resemblyzer",
            "sample_rate": 16000,
            "source_audio": str(ws.root / "audio_whisper.wav"),
            "speaker_count": len(speakers),
            "speakers": speakers,
        }
        (ws.root / "speakers.json").write_text(json.dumps(speakers_data), encoding="utf-8")

    def test_save_load_characters(self, tmp_path):
        """Basic save/load roundtrip for characters."""
        from madrac.workspace import SharedWorkspace

        ws = _make_job(tmp_path)
        self._make_speakers(ws, [
            {"speaker_id": "speaker_0", "name": "Speaker 1", "segments": [{"start": 0.0, "end": 10.0}]},
            {"speaker_id": "speaker_1", "name": "Speaker 2", "segments": [{"start": 10.0, "end": 20.0}]},
        ])

        characters = [
            {"character_id": "char_01", "name": "Lina", "speaker_id": "speaker_1", "visual_reference": None, "notes": "Main protagonist"},
            {"character_id": "char_02", "name": "Marco", "speaker_id": None, "visual_reference": "ref.png", "notes": "Villain"},
        ]
        ws.save_characters(characters)

        loaded = ws.load_characters()
        assert loaded is not None
        assert len(loaded) == 2
        assert loaded[0]["character_id"] == "char_01"
        assert loaded[0]["name"] == "Lina"
        assert loaded[0]["speaker_id"] == "speaker_1"
        assert loaded[1]["character_id"] == "char_02"
        assert loaded[1]["speaker_id"] is None
        assert ws.has_characters() is True

    def test_characters_persists_metadata_artifacts(self, tmp_path):
        """After saving characters, metadata.json shows characters artifact."""
        from madrac.workspace import SharedWorkspace

        ws = _make_job(tmp_path)
        self._make_speakers(ws, [{"speaker_id": "speaker_0", "name": "Speaker 1", "segments": []}])

        ws.save_characters([{"character_id": "char_01", "name": "Test", "speaker_id": "speaker_0"}])

        meta = ws.load_metadata()
        assert meta["artifacts"]["characters"] is True
        assert "characters_json_path" in meta
        assert meta["character_count"] == 1
        assert ws.has_characters() is True

    def test_list_characters_empty(self, tmp_path):
        """List characters when none exist."""
        from madrac.mcp.tools.recon_characters import list_characters

        ws = _make_job(tmp_path)
        self._make_speakers(ws, [{"speaker_id": "speaker_0", "name": "S1", "segments": []}])

        tool = list_characters({})
        result = asyncio.run(tool(job_id=ws.job_id))

        assert "error" not in result
        assert result["count"] == 0
        assert result["characters"] == []

    def test_set_character_create(self, tmp_path):
        """Create a new character without speaker."""
        from madrac.mcp.tools.recon_characters import set_character, list_characters

        ws = _make_job(tmp_path)
        self._make_speakers(ws, [{"speaker_id": "speaker_0", "name": "S1", "segments": []}])

        tool = set_character({})
        result = asyncio.run(tool(job_id=ws.job_id, character_id="char_01", name="Lina"))

        assert result["status"] == "done"
        assert result["character_id"] == "char_01"
        assert result["name"] == "Lina"
        assert result["speaker_id"] is None

        # Verify persisted
        list_tool = list_characters({})
        listed = asyncio.run(list_tool(job_id=ws.job_id))
        assert listed["count"] == 1
        assert listed["characters"][0]["name"] == "Lina"
        assert listed["characters"][0]["speaker_id"] is None

    def test_set_character_update(self, tmp_path):
        """Update existing character preserves speaker_id."""
        from madrac.mcp.tools.recon_characters import set_character, map_speaker_to_character, list_characters

        ws = _make_job(tmp_path)
        self._make_speakers(ws, [{"speaker_id": "speaker_0", "name": "S1", "segments": []}])

        # Create character
        set_tool = set_character({})
        asyncio.run(set_tool(job_id=ws.job_id, character_id="char_01", name="Lina"))

        # Map speaker to character
        map_tool = map_speaker_to_character({})
        asyncio.run(map_tool(job_id=ws.job_id, speaker_id="speaker_0", character_id="char_01"))

        # Update name only (speaker_id should be preserved)
        result = asyncio.run(set_tool(job_id=ws.job_id, character_id="char_01", name="Lina Updated"))

        assert result["status"] == "done"
        assert result["name"] == "Lina Updated"
        assert result["speaker_id"] == "speaker_0"

        # Verify persisted
        list_tool = list_characters({})
        listed = asyncio.run(list_tool(job_id=ws.job_id))
        assert listed["characters"][0]["speaker_id"] == "speaker_0"

    def test_set_character_requires_name(self, tmp_path):
        """set_character rejects empty name."""
        from madrac.mcp.tools.recon_characters import set_character

        ws = _make_job(tmp_path)
        self._make_speakers(ws, [{"speaker_id": "speaker_0", "name": "S1", "segments": []}])

        tool = set_character({})
        result = asyncio.run(tool(job_id=ws.job_id, character_id="char_01", name=""))

        assert "error" in result

    def test_map_speaker_to_character(self, tmp_path):
        """Map speaker to character updates both sides."""
        from madrac.mcp.tools.recon_characters import (
            set_character, map_speaker_to_character, list_characters
        )

        ws = _make_job(tmp_path)
        self._make_speakers(ws, [
            {"speaker_id": "speaker_0", "name": "Speaker 1", "segments": [{"start": 0, "end": 10}]},
            {"speaker_id": "speaker_1", "name": "Speaker 2", "segments": [{"start": 10, "end": 20}]},
        ])

        # Create characters
        set_tool = set_character({})
        asyncio.run(set_tool(job_id=ws.job_id, character_id="char_01", name="Lina"))
        asyncio.run(set_tool(job_id=ws.job_id, character_id="char_02", name="Marco"))

        # Map speaker_0 -> char_01
        map_tool = map_speaker_to_character({})
        result = asyncio.run(map_tool(job_id=ws.job_id, speaker_id="speaker_0", character_id="char_01"))

        assert result["status"] == "done"
        assert result["speaker_id"] == "speaker_0"
        assert result["character_id"] == "char_01"
        assert result["character_name"] == "Lina"

        # Verify character has speaker_id
        list_tool = list_characters({})
        listed = asyncio.run(list_tool(job_id=ws.job_id))
        char = next(c for c in listed["characters"] if c["character_id"] == "char_01")
        assert char["speaker_id"] == "speaker_0"

    def test_map_speaker_reassign(self, tmp_path):
        """Reassigning speaker updates both characters."""
        from madrac.mcp.tools.recon_characters import (
            set_character, map_speaker_to_character, list_characters
        )

        ws = _make_job(tmp_path)
        self._make_speakers(ws, [
            {"speaker_id": "speaker_0", "name": "S1", "segments": []},
            {"speaker_id": "speaker_1", "name": "S2", "segments": []},
        ])

        set_tool = set_character({})
        asyncio.run(set_tool(job_id=ws.job_id, character_id="char_01", name="A"))
        asyncio.run(set_tool(job_id=ws.job_id, character_id="char_02", name="B"))

        map_tool = map_speaker_to_character({})
        # Map speaker_0 -> char_01
        asyncio.run(map_tool(job_id=ws.job_id, speaker_id="speaker_0", character_id="char_01"))
        # Reassign speaker_0 -> char_02
        result = asyncio.run(map_tool(job_id=ws.job_id, speaker_id="speaker_0", character_id="char_02"))

        assert result["character_id"] == "char_02"

        # char_01 should have no speaker now
        list_tool = list_characters({})
        listed = asyncio.run(list_tool(job_id=ws.job_id))
        char_a = next(c for c in listed["characters"] if c["character_id"] == "char_01")
        char_b = next(c for c in listed["characters"] if c["character_id"] == "char_02")
        assert char_a["speaker_id"] is None
        assert char_b["speaker_id"] == "speaker_0"

    def test_map_speaker_invalid_speaker(self, tmp_path):
        """Mapping non-existent speaker fails."""
        from madrac.mcp.tools.recon_characters import map_speaker_to_character, set_character

        ws = _make_job(tmp_path)
        self._make_speakers(ws, [{"speaker_id": "speaker_0", "name": "S1", "segments": []}])

        set_tool = set_character({})
        asyncio.run(set_tool(job_id=ws.job_id, character_id="char_01", name="Lina"))

        map_tool = map_speaker_to_character({})
        result = asyncio.run(map_tool(job_id=ws.job_id, speaker_id="speaker_99", character_id="char_01"))

        assert "error" in result

    def test_map_speaker_invalid_character(self, tmp_path):
        """Mapping to non-existent character fails."""
        from madrac.mcp.tools.recon_characters import map_speaker_to_character, set_character

        ws = _make_job(tmp_path)
        self._make_speakers(ws, [{"speaker_id": "speaker_0", "name": "S1", "segments": []}])

        map_tool = map_speaker_to_character({})
        result = asyncio.run(map_tool(job_id=ws.job_id, speaker_id="speaker_0", character_id="char_99"))

        assert "error" in result

    def test_map_speaker_without_speakers_json(self, tmp_path):
        """Mapping fails if speakers.json missing."""
        from madrac.mcp.tools.recon_characters import map_speaker_to_character, set_character

        ws = _make_job(tmp_path)
        # No speakers.json

        set_tool = set_character({})
        asyncio.run(set_tool(job_id=ws.job_id, character_id="char_01", name="Lina"))

        map_tool = map_speaker_to_character({})
        result = asyncio.run(map_tool(job_id=ws.job_id, speaker_id="speaker_0", character_id="char_01"))

        assert "error" in result

    def test_character_without_speaker_allowed(self, tmp_path):
        """Character can exist without speaker assigned."""
        from madrac.mcp.tools.recon_characters import set_character, list_characters

        ws = _make_job(tmp_path)
        self._make_speakers(ws, [{"speaker_id": "speaker_0", "name": "S1", "segments": []}])

        set_tool = set_character({})
        asyncio.run(set_tool(job_id=ws.job_id, character_id="char_01", name="Pre-production"))

        list_tool = list_characters({})
        listed = asyncio.run(list_tool(job_id=ws.job_id))
        assert listed["characters"][0]["speaker_id"] is None

    def test_rename_character_preserves_speakers_json(self, tmp_path):
        """Renaming character does not modify speakers.json."""
        from madrac.mcp.tools.recon_characters import set_character, list_characters

        ws = _make_job(tmp_path)
        self._make_speakers(ws, [{"speaker_id": "speaker_0", "name": "Original", "segments": []}])

        set_tool = set_character({})
        asyncio.run(set_tool(job_id=ws.job_id, character_id="char_01", name="Lina"))
        asyncio.run(set_tool(job_id=ws.job_id, character_id="char_01", name="Lina Updated"))

        # speakers.json unchanged
        speakers = json.loads((ws.root / "speakers.json").read_text(encoding="utf-8"))
        assert speakers["speakers"][0]["name"] == "Original"

        # character name updated
        list_tool = list_characters({})
        listed = asyncio.run(list_tool(job_id=ws.job_id))
        assert listed["characters"][0]["name"] == "Lina Updated"