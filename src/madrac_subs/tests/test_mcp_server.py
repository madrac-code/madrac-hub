"""
Tests for MADRAC MCP Server.

Tests use a mock app_state to avoid requiring a running MADRAC instance.
"""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_queue_manager():
    qm = MagicMock()
    qm.pending_count.return_value = 2
    qm.active_count.return_value = 1
    qm.completed_count.return_value = 10
    qm.total_count.return_value = 13
    qm.pause.return_value = None
    qm.add_file.return_value = "job_001"
    return qm


@pytest.fixture
def mock_dubbing_manager():
    dm = MagicMock()
    dm.get_status.return_value = {"status": "running", "progress": 0.5}
    dm.get_all_status.return_value = []
    dm.start_job.return_value = "dub_001"
    return dm


@pytest.fixture
def mock_assistant_manager():
    am = MagicMock()
    am.execute_action.return_value = "OK"
    return am


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.to_dict.return_value = {"whisper": {"modelo": "medium"}}
    return config


@pytest.fixture
def app_state(mock_queue_manager, mock_dubbing_manager,
              mock_assistant_manager, mock_config):
    return {
        "queue_manager": mock_queue_manager,
        "dubbing_manager": mock_dubbing_manager,
        "assistant_manager": mock_assistant_manager,
        "config": mock_config,
    }


class TestQueueTools:
    @pytest.mark.asyncio
    async def test_get_queue_status_returns_counts(self, app_state):
        from madrac.mcp.tools.queue import get_queue_status
        tool = get_queue_status(app_state)
        result = await tool()
        assert result["pendientes"] == 2
        assert result["en_progreso"] == 1
        assert result["completados"] == 10
        assert result["total"] == 13

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

    @pytest.mark.asyncio
    async def test_pause_processing_no_manager(self):
        from madrac.mcp.tools.queue import pause_processing
        tool = pause_processing({})
        result = await tool()
        assert result is False


class TestTranscriptionTools:
    @pytest.mark.asyncio
    async def test_transcribe_file_queues_job(self, app_state):
        from madrac.mcp.tools.transcription import transcribe_file
        tool = transcribe_file(app_state)
        result = await tool("/path/to/video.mp4", "es")
        assert "job_001" in result

    @pytest.mark.asyncio
    async def test_transcribe_file_no_manager(self):
        from madrac.mcp.tools.transcription import transcribe_file
        tool = transcribe_file({})
        result = await tool("/path/to/video.mp4")
        assert "Error" in result


class TestAssistantTools:
    @pytest.mark.asyncio
    async def test_execute_action_calls_manager(self, app_state):
        from madrac.mcp.tools.assistant import execute_assistant_action
        tool = execute_assistant_action(app_state)
        result = await tool("obtener_hora")
        assert result == "OK"

    @pytest.mark.asyncio
    async def test_execute_action_no_manager(self):
        from madrac.mcp.tools.assistant import execute_assistant_action
        tool = execute_assistant_action({})
        result = await tool("obtener_hora")
        assert "Error" in result


class TestDubbingTools:
    @pytest.mark.asyncio
    async def test_start_dubbing_returns_job_id(self, app_state):
        from madrac.mcp.tools.dubbing import start_dubbing
        tool = start_dubbing(app_state)
        result = await tool("/path/to/video.mp4", "es")
        assert "dub_001" in result

    @pytest.mark.asyncio
    async def test_get_dubbing_status_with_job_id(self, app_state):
        from madrac.mcp.tools.dubbing import get_dubbing_status
        tool = get_dubbing_status(app_state)
        result = await tool("dub_001")
        assert result["status"] == "running"


class TestConfigTools:
    @pytest.mark.asyncio
    async def test_read_config_full(self, app_state):
        from madrac.mcp.tools.config import read_config
        tool = read_config(app_state)
        result = await tool()
        assert "whisper" in result

    @pytest.mark.asyncio
    async def test_read_config_no_manager(self):
        from madrac.mcp.tools.config import read_config
        tool = read_config({})
        result = await tool()
        assert "error" in result
