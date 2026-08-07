# ─── Workspace MCP Tool Tests ─────────────────────────────────────

import pytest
from unittest.mock import patch
from pathlib import Path

from madrac.mcp.tools.workspace import (
    edit_subtitle_segment,
    export_srt,
    get_segments,
    get_workspace_info,
    list_workspaces,
    rename_speaker,
)
from madrac.workspace.shared import SharedWorkspace


class TestEditSubtitleSegment:
    """Tests for edit_subtitle_segment tool."""

    @pytest.fixture
    def workspace_with_segments(self, tmp_path):
        """Create a workspace with test segments."""
        video = tmp_path / "test.mp4"
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)
        segments = [
            {"start": 0.0, "end": 1.0, "text": "gracias"},
            {"start": 1.0, "end": 2.0, "text": "hola mundo"},
        ]
        ws.save_segments(segments, language="es")
        return ws

    @pytest.mark.asyncio
    async def test_edit_segment_changes_text(self, workspace_with_segments):
        ws = workspace_with_segments
        tool = edit_subtitle_segment({})
        with patch("madrac.mcp.tools.workspace.SharedWorkspace.from_job_id",
                   return_value=ws):
            result = await tool(ws.job_id, 0, "thank you")
        assert result["success"] is True
        assert result["old_text"] == "gracias"
        assert result["new_text"] == "thank you"
        loaded = ws.load_segments()
        assert loaded["segments"][0]["text"] == "thank you"
        assert loaded["segments"][1]["text"] == "hola mundo"

    @pytest.mark.asyncio
    async def test_edit_nonexistent_segment(self, workspace_with_segments):
        ws = workspace_with_segments
        tool = edit_subtitle_segment({})
        with patch("madrac.mcp.tools.workspace.SharedWorkspace.from_job_id",
                   return_value=ws):
            result = await tool(ws.job_id, 99, "new text")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_edit_no_segments(self, tmp_path):
        video = tmp_path / "empty.mp4"
        video.write_bytes(b"empty")
        ws = SharedWorkspace.open(video)
        tool = edit_subtitle_segment({})
        with patch("madrac.mcp.tools.workspace.SharedWorkspace.from_job_id",
                   return_value=ws):
            result = await tool(ws.job_id, 0, "test")
        assert "error" in result


class TestExportSrt:
    """Tests for export_srt tool."""

    @pytest.fixture
    def workspace_with_segments(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)
        segments = [
            {"start": 0.0, "end": 1.5, "text": "thank you"},
            {"start": 1.5, "end": 3.0, "text": "hello world"},
        ]
        ws.save_segments(segments, language="en")
        return ws

    @pytest.mark.asyncio
    async def test_export_creates_srt_file(self, workspace_with_segments, tmp_path):
        ws = workspace_with_segments
        output = str(tmp_path / "output.srt")
        tool = export_srt({})
        with patch("madrac.mcp.tools.workspace.SharedWorkspace.from_job_id",
                   return_value=ws):
            result = await tool(ws.job_id, output_path=output)
        assert result["success"] is True
        assert result["segment_count"] == 2
        content = Path(output).read_text(encoding="utf-8")
        assert "thank you" in content
        assert "00:00:00,000 --> 00:00:01,500" in content

    @pytest.mark.asyncio
    async def test_export_no_segments_returns_error(self, tmp_path):
        video = tmp_path / "empty.mp4"
        video.write_bytes(b"empty")
        ws = SharedWorkspace.open(video)
        tool = export_srt({})
        with patch("madrac.mcp.tools.workspace.SharedWorkspace.from_job_id",
                   return_value=ws):
            result = await tool(ws.job_id)
        assert "error" in result


class TestGetSegments:
    """Tests for get_segments tool."""

    @pytest.fixture
    def workspace_with_segments(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)
        segments = [
            {"start": 0.0, "end": 1.0, "text": "hello"},
            {"start": 1.0, "end": 2.0, "text": "world"},
        ]
        ws.save_segments(segments, language="en")
        return ws

    @pytest.mark.asyncio
    async def test_get_segments_returns_all(self, workspace_with_segments):
        ws = workspace_with_segments
        tool = get_segments({})
        with patch("madrac.mcp.tools.workspace.SharedWorkspace.from_job_id",
                   return_value=ws):
            result = await tool(ws.job_id)
        assert "segments" in result
        assert len(result["segments"]) == 2
        assert result["segments"][0]["text"] == "hello"
        assert result["segments"][1]["text"] == "world"

    @pytest.mark.asyncio
    async def test_get_segments_nonexistent(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.write_bytes(b"test")
        ws = SharedWorkspace.open(video)
        tool = get_segments({})
        with patch("madrac.mcp.tools.workspace.SharedWorkspace.from_job_id",
                   return_value=ws):
            result = await tool(ws.job_id)
        assert "error" in result


class TestGetWorkspaceInfo:
    """Tests for get_workspace_info tool."""

    @pytest.fixture
    def workspace_with_data(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.write_bytes(b"test content")
        ws = SharedWorkspace.open(video)
        # Add whisper audio
        (tmp_path / "audio.wav").write_bytes(b"audio")
        ws.save_whisper_audio(tmp_path / "audio.wav", duration_s=10.0)
        # Add segments
        ws.save_segments([{"start": 0, "end": 1, "text": "test"}], "en")
        return ws

    @pytest.mark.asyncio
    async def test_get_workspace_info_returns_artifacts(self, workspace_with_data):
        ws = workspace_with_data
        tool = get_workspace_info({})
        with patch("madrac.mcp.tools.workspace.SharedWorkspace.from_job_id",
                   return_value=ws):
            result = await tool(ws.job_id)
        assert result["job_id"] == ws.job_id
        assert result["artifacts"]["whisper_audio"] is True
        assert result["artifacts"]["segments"] is True

    @pytest.mark.asyncio
    async def test_get_workspace_info_nonexistent(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.write_bytes(b"test")
        ws = SharedWorkspace.open(video)
        tool = get_workspace_info({})
        with patch("madrac.mcp.tools.workspace.SharedWorkspace.from_job_id",
                   return_value=ws):
            result = await tool(ws.job_id)
        # Workspace exists but has no artifacts
        assert "error" not in result
        assert result["job_id"] == ws.job_id
        assert all(v is False for v in result["artifacts"].values())


class TestListWorkspaces:
    """Tests for list_workspaces tool."""

    @pytest.mark.asyncio
    async def test_list_workspaces_returns_list(self):
        """list_workspaces returns a list of workspaces with correct structure."""
        tool = list_workspaces({})
        result = await tool()
        assert "workspaces" in result
        assert isinstance(result["workspaces"], list)
        # Each workspace should have expected fields
        for ws in result["workspaces"]:
            assert "job_id" in ws
            assert "source_video" in ws
            assert "updated_at" in ws
            assert "artifacts" in ws
            assert isinstance(ws["artifacts"], dict)
            for key in ("whisper_audio", "full_audio", "segments", "stems"):
                assert key in ws["artifacts"]


class TestRenameSpeaker:
    """Tests for rename_speaker tool."""

    @pytest.fixture
    def workspace_with_speakers(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.write_bytes(b"test")
        ws = SharedWorkspace.open(video)
        ws.update_metadata(speakers={0: "Speaker 1", 1: "Speaker 2"})
        return ws

    @pytest.mark.asyncio
    async def test_rename_speaker_success(self, workspace_with_speakers):
        ws = workspace_with_speakers
        tool = rename_speaker({})
        with patch("madrac.mcp.tools.workspace.SharedWorkspace.from_job_id",
                   return_value=ws):
            result = await tool(ws.job_id, 0, "Alice")
        assert result["success"] is True
        assert result["old_name"] == "Speaker 1"
        assert result["new_name"] == "Alice"
        meta = ws.load_metadata()
        assert meta["speakers"]["0"] == "Alice"

    @pytest.mark.asyncio
    async def test_rename_nonexistent_speaker(self, workspace_with_speakers):
        ws = workspace_with_speakers
        tool = rename_speaker({})
        with patch("madrac.mcp.tools.workspace.SharedWorkspace.from_job_id",
                   return_value=ws):
            result = await tool(ws.job_id, 99, "Unknown")
        assert "error" in result