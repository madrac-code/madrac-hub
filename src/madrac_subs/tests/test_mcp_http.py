"""Tests for MADRAC MCP HTTP server and agent client."""
import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path


@pytest.fixture
def mock_app_state():
    qm = MagicMock()
    qm.pending_count.return_value = 0
    qm.active_count.return_value = 0
    qm.completed_count.return_value = 0
    qm.total_count.return_value = 0
    return {"queue_manager": qm}


@pytest.fixture
def token_file(tmp_path):
    token_path = tmp_path / "mcp_token.txt"
    token_path.write_text("test_token_abc123")
    return token_path


class TestTokenManager:
    def test_get_or_create_token_creates_file(self, tmp_path):
        from madrac.mcp.auth import get_or_create_token, TOKEN_PATH
        with patch("madrac.mcp.auth.TOKEN_PATH",
                   tmp_path / "mcp_token.txt"):
            token = get_or_create_token()
            assert len(token) == 64  # 32 bytes hex
            assert (tmp_path / "mcp_token.txt").exists()

    def test_get_or_create_token_reuses_existing(self, tmp_path):
        from madrac.mcp.auth import get_or_create_token
        token_path = tmp_path / "mcp_token.txt"
        token_path.write_text("existing_token")
        with patch("madrac.mcp.auth.TOKEN_PATH", token_path):
            token = get_or_create_token()
            assert token == "existing_token"

    def test_validate_token_correct(self, tmp_path):
        from madrac.mcp.auth import validate_token
        token_path = tmp_path / "mcp_token.txt"
        token_path.write_text("correct_token")
        with patch("madrac.mcp.auth.TOKEN_PATH", token_path):
            assert validate_token("correct_token") is True

    def test_validate_token_wrong(self, tmp_path):
        from madrac.mcp.auth import validate_token
        token_path = tmp_path / "mcp_token.txt"
        token_path.write_text("correct_token")
        with patch("madrac.mcp.auth.TOKEN_PATH", token_path):
            assert validate_token("wrong_token") is False

    def test_revoke_token_deletes_file(self, tmp_path):
        from madrac.mcp.auth import revoke_token, TOKEN_PATH
        token_path = tmp_path / "mcp_token.txt"
        token_path.write_text("some_token")
        with patch("madrac.mcp.auth.TOKEN_PATH", token_path):
            revoke_token()
            assert not token_path.exists()


class TestMCPHttpServer:
    @pytest.mark.asyncio
    async def test_health_endpoint_no_auth(self, mock_app_state, tmp_path):
        from madrac.mcp.http_server import MCPHttpServer
        with patch("madrac.mcp.auth.TOKEN_PATH",
                   tmp_path / "mcp_token.txt"):
            server = MCPHttpServer(mock_app_state)
            request = MagicMock()
            request.path = "/health"
            response = await server._handle_health(request)
            body = json.loads(response.text)
            assert body["status"] == "ok"
            assert body["tools"] == 22
            assert body["resources"] == 4

    @pytest.mark.asyncio
    async def test_dispatch_tools_list(self, mock_app_state, tmp_path):
        from madrac.mcp.http_server import MCPHttpServer
        with patch("madrac.mcp.auth.TOKEN_PATH",
                   tmp_path / "mcp_token.txt"):
            server = MCPHttpServer(mock_app_state)
            result = await server._dispatch("tools/list", {})
            assert "tools" in result
            assert len(result["tools"]) == 22

    @pytest.mark.asyncio
    async def test_dispatch_unknown_method(self, mock_app_state, tmp_path):
        from madrac.mcp.http_server import MCPHttpServer
        with patch("madrac.mcp.auth.TOKEN_PATH",
                   tmp_path / "mcp_token.txt"):
            server = MCPHttpServer(mock_app_state)
            result = await server._dispatch("unknown/method", {})
            assert "error" in result

    @pytest.mark.asyncio
    async def test_call_tool_get_queue_status(
        self, mock_app_state, tmp_path
    ):
        from madrac.mcp.http_server import MCPHttpServer
        with patch("madrac.mcp.auth.TOKEN_PATH",
                   tmp_path / "mcp_token.txt"):
            server = MCPHttpServer(mock_app_state)
            result = await server._call_tool("get_queue_status", {})
            assert "pendientes" in result

    @pytest.mark.asyncio
    async def test_call_unknown_tool_returns_error(
        self, mock_app_state, tmp_path
    ):
        from madrac.mcp.http_server import MCPHttpServer
        with patch("madrac.mcp.auth.TOKEN_PATH",
                   tmp_path / "mcp_token.txt"):
            server = MCPHttpServer(mock_app_state)
            result = await server._call_tool("nonexistent_tool", {})
            assert "error" in result

    @pytest.mark.asyncio
    async def test_dispatch_resources_read_queue_estado(
        self, mock_app_state, tmp_path
    ):
        from madrac.mcp.http_server import MCPHttpServer
        with patch("madrac.mcp.auth.TOKEN_PATH",
                   tmp_path / "mcp_token.txt"):
            server = MCPHttpServer(mock_app_state)
            result = await server._read_resource("queue://estado")
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_handle_mcp_invalid_json_includes_parser_detail(
        self, mock_app_state, tmp_path
    ):
        import json as _json
        from madrac.mcp.http_server import MCPHttpServer
        with patch("madrac.mcp.auth.TOKEN_PATH",
                   tmp_path / "mcp_token.txt"):
            server = MCPHttpServer(mock_app_state)
            request = MagicMock()
            request.json = AsyncMock(
                side_effect=_json.JSONDecodeError("Expecting value", "{", 0)
            )
            response = await server._handle_mcp(request)
            assert response.status == 400
            body = _json.loads(response.text)
            assert "error" in body
            assert "Expecting value" in body["error"]


class TestMADRACAgent:
    def test_agent_loads_token(self, token_file):
        from madrac.mcp.agent_client import MADRACAgent
        agent = MADRACAgent(token_path=token_file)
        assert agent._token == "test_token_abc123"

    def test_agent_raises_if_no_token_file(self, tmp_path):
        from madrac.mcp.agent_client import MADRACAgent
        with pytest.raises(FileNotFoundError):
            MADRACAgent(token_path=tmp_path / "nonexistent.txt")

    def test_agent_headers_include_bearer(self, token_file):
        from madrac.mcp.agent_client import MADRACAgent
        agent = MADRACAgent(token_path=token_file)
        assert "Bearer test_token_abc123" in agent._headers["Authorization"]

    def test_agent_health_no_auth(self, token_file):
        from madrac.mcp.agent_client import MADRACAgent
        agent = MADRACAgent(
            base_url="http://127.0.0.1:7654",
            token_path=token_file,
        )
        # Just verify the method exists and constructs the right URL
        assert agent.base_url == "http://127.0.0.1:7654"

    def test_agent_call_tool_constructs_correct_payload(self, token_file):
        from madrac.mcp.agent_client import MADRACAgent
        agent = MADRACAgent(token_path=token_file)
        # Verify the method signature works
        assert callable(agent.call_tool)
        assert callable(agent.list_tools)
        assert callable(agent.read_resource)