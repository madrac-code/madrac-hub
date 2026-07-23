"""
Tests for MADRAC MCP Server.

Uses real QueueEntry/ProcessingState from madrac.pipeline.queue and mocks for
QueueManager, DubbingManager, ConfigManager, PipelineWorker, AssistantManager.
"""
import pytest
from unittest.mock import MagicMock
from pathlib import Path

from madrac.pipeline.queue import QueueEntry, ProcessingState


@pytest.fixture
def mock_queue_manager():
    qm = MagicMock()
    entries = [
        QueueEntry.new("/videos/a.mp4"),
        QueueEntry.new("/videos/b.mp4"),
        QueueEntry.new("/videos/c.mp4"),
    ]
    entries[0].state = ProcessingState.PENDING
    entries[1].state = ProcessingState.PROCESSING
    entries[2].state = ProcessingState.COMPLETED

    # Add a couple more completed ones
    for _ in range(7):
        e = QueueEntry.new("/videos/x.mp4")
        e.state = ProcessingState.COMPLETED
        entries.append(e)
    # One failed
    e = QueueEntry.new("/videos/fail.mp4")
    e.state = ProcessingState.FAILED
    entries.append(e)

    qm.list_all.return_value = entries

    new_entry = QueueEntry.new("/videos/new.mp4")
    qm.add.return_value = new_entry
    return qm


@pytest.fixture
def mock_worker():
    w = MagicMock()
    w.pause = MagicMock()
    w.resume = MagicMock()
    return w


@pytest.fixture
def mock_dubbing_manager():
    dm = MagicMock()
    dm._process = MagicMock()
    dm._process.poll.return_value = None  # subprocess is running
    dm.poll_job.return_value = {"status": "running", "progress_pct": 50}
    dm.submit_job.return_value = "dub_001"
    dm.launch_dubs.return_value = True
    return dm


@pytest.fixture
def mock_assistant_manager():
    am = MagicMock()
    am.execute_action.return_value = "OK"
    return am


@pytest.fixture
def mock_config_manager():
    cfg = MagicMock()
    cfg.get_all.return_value = {"whisper": {"modelo": "medium"}, "version": 3}
    cfg.get.return_value = "medium"
    return cfg


@pytest.fixture
def app_state(mock_queue_manager, mock_worker, mock_dubbing_manager,
              mock_assistant_manager, mock_config_manager):
    return {
        "queue_manager": mock_queue_manager,
        "worker": mock_worker,
        "dubbing_manager": mock_dubbing_manager,
        "assistant_manager": mock_assistant_manager,
        "config_manager": mock_config_manager,
    }


class TestQueueTools:
    @pytest.mark.asyncio
    async def test_get_queue_status_returns_counts(self, app_state):
        from madrac.mcp.tools.queue import get_queue_status
        tool = get_queue_status(app_state)
        result = await tool()
        assert result["pendientes"] == 1
        assert result["en_progreso"] == 1
        assert result["completados"] == 8
        assert result["fallidos"] == 1
        assert result["total"] == 11

    @pytest.mark.asyncio
    async def test_get_queue_status_no_manager(self):
        from madrac.mcp.tools.queue import get_queue_status
        tool = get_queue_status({})
        result = await tool()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_pause_processing_returns_true(self, app_state):
        from madrac.mcp.tools.queue import pause_processing
        tool = pause_processing(app_state)
        result = await tool()
        assert result is True
        app_state["worker"].pause.assert_called_once()

    @pytest.mark.asyncio
    async def test_pause_processing_no_worker(self):
        from madrac.mcp.tools.queue import pause_processing
        tool = pause_processing({})
        result = await tool()
        assert result is False

    @pytest.mark.asyncio
    async def test_resume_processing_returns_true(self, app_state):
        from madrac.mcp.tools.queue import resume_processing
        tool = resume_processing(app_state)
        result = await tool()
        assert result is True
        app_state["worker"].resume.assert_called_once()


class TestTranscriptionTools:
    @pytest.mark.asyncio
    async def test_transcribe_file_queues_job(self, app_state, tmp_path):
        from madrac.mcp.tools.transcription import transcribe_file
        video = tmp_path / "test.mp4"
        video.write_text("fake video content")
        tool = transcribe_file(app_state)
        result = await tool(str(video), "es")
        assert "queued" in result.lower()
        app_state["queue_manager"].add.assert_called_once_with(str(video))

    @pytest.mark.asyncio
    async def test_transcribe_file_no_manager(self):
        from madrac.mcp.tools.transcription import transcribe_file
        tool = transcribe_file({})
        result = await tool("/path/to/video.mp4")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_transcribe_file_not_found(self, app_state):
        from madrac.mcp.tools.transcription import transcribe_file
        tool = transcribe_file(app_state)
        result = await tool("/nonexistent/file.mp4")
        assert "Error" in result
        app_state["queue_manager"].add.assert_not_called()


class TestAssistantTools:
    @pytest.mark.asyncio
    async def test_execute_action_calls_manager(self, app_state):
        from madrac.mcp.tools.assistant import execute_assistant_action
        tool = execute_assistant_action(app_state)
        result = await tool("obtener_hora")
        assert result == "OK"
        app_state["assistant_manager"].execute_action.assert_called_once_with("obtener_hora", "")

    @pytest.mark.asyncio
    async def test_execute_action_no_manager(self):
        from madrac.mcp.tools.assistant import execute_assistant_action
        tool = execute_assistant_action({})
        result = await tool("obtener_hora")
        assert "Error" in result


class TestDubbingTools:
    @pytest.mark.asyncio
    async def test_start_dubbing_returns_job_id(self, app_state, tmp_path):
        from madrac.mcp.tools.dubbing import start_dubbing
        video = tmp_path / "movie.mp4"
        srt = tmp_path / "movie.srt"
        video.write_text("video")
        srt.write_text("1\n00:00:01,000 --> 00:00:04,000\nHello")
        tool = start_dubbing(app_state)
        result = await tool(str(video), str(srt), str(tmp_path / "dubbed.mp4"), "es")
        assert "dub_001" in result
        app_state["dubbing_manager"].submit_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dubbing_status_with_job_id(self, app_state):
        from madrac.mcp.tools.dubbing import get_dubbing_status
        tool = get_dubbing_status(app_state)
        result = await tool("dub_001")
        assert result["status"] == "running"
        app_state["dubbing_manager"].poll_job.assert_called_once_with("dub_001")


class TestConfigTools:
    @pytest.mark.asyncio
    async def test_read_config_full(self, app_state):
        from madrac.mcp.tools.config import read_config
        tool = read_config(app_state)
        result = await tool()
        assert "whisper" in result
        assert result["whisper"]["modelo"] == "medium"

    @pytest.mark.asyncio
    async def test_read_config_by_key(self, app_state):
        from madrac.mcp.tools.config import read_config
        tool = read_config(app_state)
        result = await tool("whisper.modelo")
        assert result["value"] == "medium"

    @pytest.mark.asyncio
    async def test_read_config_no_manager(self):
        from madrac.mcp.tools.config import read_config
        tool = read_config({})
        result = await tool()
        assert "error" in result


class TestQueueResources:
    @pytest.mark.asyncio
    async def test_estado_resource_returns_summary(self, app_state):
        from madrac.mcp.resources.queue import get_queue_estado_resource
        import json
        handler = get_queue_estado_resource(app_state)
        raw = await handler()
        data = json.loads(raw)
        assert data["pendientes"] == 1
        assert data["en_progreso"] == 1
        assert data["completados"] == 8
        assert data["fallidos"] == 1
        assert data["total"] == 11
        assert len(data["items"]) > 0
        assert "id" in data["items"][0]
        assert "state" in data["items"][0]

    @pytest.mark.asyncio
    async def test_estado_resource_no_manager(self):
        from madrac.mcp.resources.queue import get_queue_estado_resource
        import json
        handler = get_queue_estado_resource({})
        raw = await handler()
        data = json.loads(raw)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_progreso_resource_returns_item(self, app_state):
        from madrac.mcp.resources.queue import get_queue_progreso_resource
        import json
        # Find the first entry's id from the mock
        from madrac.pipeline.queue import ProcessingState
        all_items = app_state["queue_manager"].list_all()
        target_id = all_items[0].id
        handler = get_queue_progreso_resource(app_state)
        raw = await handler(target_id)
        data = json.loads(raw)
        assert data["id"] == target_id
        assert "state" in data
        assert "filename" in data

    @pytest.mark.asyncio
    async def test_progreso_resource_not_found(self, app_state):
        from madrac.mcp.resources.queue import get_queue_progreso_resource
        import json
        handler = get_queue_progreso_resource(app_state)
        raw = await handler("nonexistent_id")
        data = json.loads(raw)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_progreso_resource_no_manager(self):
        from madrac.mcp.resources.queue import get_queue_progreso_resource
        import json
        handler = get_queue_progreso_resource({})
        raw = await handler("any_id")
        data = json.loads(raw)
        assert "error" in data


class TestConfigResources:
    @pytest.mark.asyncio
    async def test_actual_resource_returns_config(self, app_state):
        from madrac.mcp.resources.config import get_config_actual_resource
        import json
        handler = get_config_actual_resource(app_state)
        raw = await handler()
        data = json.loads(raw)
        assert data["whisper"]["modelo"] == "medium"
        assert data["version"] == 3

    @pytest.mark.asyncio
    async def test_actual_resource_no_manager(self):
        from madrac.mcp.resources.config import get_config_actual_resource
        import json
        handler = get_config_actual_resource({})
        raw = await handler()
        data = json.loads(raw)
        assert "error" in data


class TestLogResources:
    @pytest.mark.asyncio
    async def test_ultimos_returns_entries(self, app_state):
        from madrac.mcp.resources.logs import get_ultimos_logs_resource
        from collections import deque
        import json
        buf = deque(maxlen=100)
        buf.append({"time": "t1", "level": "INFO", "name": "test", "message": "hello"})
        buf.append({"time": "t2", "level": "WARN", "name": "test", "message": "world"})
        app_state["log_buffer"] = buf
        handler = get_ultimos_logs_resource(app_state)
        raw = await handler(10)
        data = json.loads(raw)
        assert len(data) == 2
        assert data[0]["message"] == "hello"

    @pytest.mark.asyncio
    async def test_ultimos_no_buffer(self, app_state):
        from madrac.mcp.resources.logs import get_ultimos_logs_resource
        import json
        handler = get_ultimos_logs_resource(app_state)
        raw = await handler(10)
        data = json.loads(raw)
        assert "error" in data
        assert "note" in data

    @pytest.mark.asyncio
    async def test_ultimos_respects_n(self, app_state):
        from madrac.mcp.resources.logs import get_ultimos_logs_resource
        from collections import deque
        import json
        buf = deque(maxlen=100)
        for i in range(10):
            buf.append({"time": f"t{i}", "level": "INFO", "name": "t", "message": str(i)})
        app_state["log_buffer"] = buf
        handler = get_ultimos_logs_resource(app_state)
        raw = await handler(3)
        data = json.loads(raw)
        assert len(data) == 3
        assert data[-1]["message"] == "9"


class TestServerCreation:
    def test_create_server_returns_fastmcp(self, app_state):
        from madrac.mcp.server import create_server
        server = create_server(app_state)
        assert server is not None
        assert server.name == "madrac-subs"
