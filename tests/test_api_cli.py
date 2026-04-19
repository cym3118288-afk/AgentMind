"""Tests for API server and CLI functionality."""

import pytest
import asyncio
import json
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

from agentmind import Agent, AgentMind
from agentmind.llm import LLMProvider, LLMResponse

# Check for optional dependencies
try:
    from fastapi.testclient import TestClient

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    TestClient = None

try:
    from click.testing import CliRunner

    CLICK_AVAILABLE = True
except ImportError:
    CLICK_AVAILABLE = False
    CliRunner = None


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, model="mock-model", **kwargs):
        super().__init__(model, **kwargs)

    async def generate(self, messages, temperature=None, max_tokens=None, **kwargs):
        """Generate a mock response."""
        return LLMResponse(
            content="Mock collaboration result",
            model=self.model,
            usage={"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50},
            metadata={},
        )

    async def generate_stream(self, messages, temperature=None, max_tokens=None, **kwargs):
        """Generate a mock streaming response."""
        for chunk in ["Mock ", "stream ", "result"]:
            yield chunk


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
class TestAPIServer:
    """Test FastAPI server endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api_server import app

        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["name"] == "AgentMind API"

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "active_sessions" in data

    def test_list_sessions_empty(self, client):
        """Test listing sessions when none exist."""
        response = client.get("/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "sessions" in data

    @patch("api_server.create_llm_provider")
    @patch("agentmind.AgentMind.collaborate")
    def test_collaborate_endpoint(self, mock_collaborate, mock_provider, client):
        """Test collaboration endpoint."""
        # Setup mocks
        mock_provider.return_value = MockLLMProvider()
        mock_collaborate.return_value = "Mock result"

        # Create request
        request_data = {
            "task": "Test task",
            "agents": [
                {"name": "Agent1", "role": "assistant"},
                {"name": "Agent2", "role": "reviewer"},
            ],
            "max_rounds": 2,
            "llm_provider": "ollama",
            "llm_model": "llama3.2",
            "temperature": 0.7,
        }

        response = client.post("/collaborate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "result" in data
        assert "duration_ms" in data

    def test_collaborate_invalid_request(self, client):
        """Test collaboration with invalid request."""
        request_data = {"task": "Test task", "agents": [], "max_rounds": 2}  # Empty agents list

        response = client.post("/collaborate", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_collaborate_invalid_rounds(self, client):
        """Test collaboration with invalid rounds."""
        request_data = {
            "task": "Test task",
            "agents": [{"name": "Agent1", "role": "assistant"}],
            "max_rounds": 25,  # Exceeds maximum
        }

        response = client.post("/collaborate", json=request_data)
        assert response.status_code == 422

    def test_get_session_not_found(self, client):
        """Test getting non-existent session."""
        response = client.get("/session/nonexistent-id")
        assert response.status_code == 404

    def test_delete_session_not_found(self, client):
        """Test deleting non-existent session."""
        response = client.delete("/session/nonexistent-id")
        assert response.status_code == 404

    @patch("api_server.create_llm_provider")
    @patch("agentmind.AgentMind.collaborate")
    def test_session_lifecycle(self, mock_collaborate, mock_provider, client):
        """Test complete session lifecycle."""
        # Setup mocks
        mock_provider.return_value = MockLLMProvider()
        mock_collaborate.return_value = "Mock result"

        # Create session
        request_data = {
            "task": "Test task",
            "agents": [{"name": "Agent1", "role": "assistant"}],
            "max_rounds": 1,
        }

        create_response = client.post("/collaborate", json=request_data)
        assert create_response.status_code == 200
        session_id = create_response.json()["session_id"]

        # Get session status
        status_response = client.get(f"/session/{session_id}")
        assert status_response.status_code == 200
        assert status_response.json()["session_id"] == session_id

        # Delete session
        delete_response = client.delete(f"/session/{session_id}")
        assert delete_response.status_code == 200

        # Verify deletion
        get_response = client.get(f"/session/{session_id}")
        assert get_response.status_code == 404


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
class TestAPIModels:
    """Test API request/response models."""

    def test_agent_config_validation(self):
        """Test AgentConfig validation."""
        from api_server import AgentConfig

        # Valid config
        config = AgentConfig(name="TestAgent", role="assistant")
        assert config.name == "TestAgent"
        assert config.role == "assistant"
        assert config.tools == []

        # With tools
        config_with_tools = AgentConfig(
            name="TestAgent", role="assistant", tools=["search", "calculator"]
        )
        assert len(config_with_tools.tools) == 2

    def test_collaboration_request_validation(self):
        """Test CollaborationRequest validation."""
        from api_server import CollaborationRequest, AgentConfig

        # Valid request
        request = CollaborationRequest(
            task="Test task", agents=[AgentConfig(name="Agent1", role="assistant")], max_rounds=5
        )
        assert request.task == "Test task"
        assert len(request.agents) == 1
        assert request.max_rounds == 5

    def test_collaboration_request_defaults(self):
        """Test CollaborationRequest default values."""
        from api_server import CollaborationRequest, AgentConfig

        request = CollaborationRequest(
            task="Test task", agents=[AgentConfig(name="Agent1", role="assistant")]
        )
        assert request.max_rounds == 5
        assert request.llm_provider == "ollama"
        assert request.llm_model == "llama3.2"
        assert request.temperature == 0.7
        assert request.stream is False
        assert request.enable_tracing is True


@pytest.mark.skipif(not CLICK_AVAILABLE, reason="Click not installed")
class TestCLICommands:
    """Test CLI command functionality."""

    @pytest.mark.asyncio
    async def test_create_llm_provider_ollama(self):
        """Test creating Ollama provider."""
        from cli import create_llm_provider

        provider = create_llm_provider("ollama", "llama3.2", 0.7)
        assert provider is not None
        assert provider.model == "llama3.2"

    @pytest.mark.asyncio
    async def test_create_llm_provider_litellm(self):
        """Test creating LiteLLM provider."""
        pytest.skip("LiteLLM not installed")
        from cli import create_llm_provider

        provider = create_llm_provider("openai", "gpt-4", 0.8)
        assert provider is not None
        assert provider.model == "gpt-4"

    def test_create_default_agents(self):
        """Test creating default agents."""
        from cli import create_default_agents

        provider = MockLLMProvider()
        agents = create_default_agents(provider, 3)

        assert len(agents) == 3
        assert all(isinstance(agent, Agent) for agent in agents)
        assert agents[0].name == "Analyst"
        assert agents[1].name == "Researcher"
        assert agents[2].name == "Strategist"

    def test_create_default_agents_max_limit(self):
        """Test creating agents respects maximum."""
        from cli import create_default_agents

        provider = MockLLMProvider()
        agents = create_default_agents(provider, 10)

        # Should only create 5 agents (max available roles)
        assert len(agents) == 5

    @patch("cli.console")
    def test_cli_version_command(self, mock_console):
        """Test version command."""
        from click.testing import CliRunner
        from cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.3.0" in result.output

    @patch("cli.console")
    def test_cli_examples_command(self, mock_console):
        """Test examples command."""
        from click.testing import CliRunner
        from cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["examples"])
        assert result.exit_code == 0


@pytest.mark.skipif(not CLICK_AVAILABLE, reason="Click not installed")
class TestCLIValidation:
    """Test CLI input validation."""

    @patch("cli.asyncio.run")
    @patch("cli.console")
    def test_run_command_invalid_agents(self, mock_console, mock_run):
        """Test run command with invalid agent count."""
        from click.testing import CliRunner
        from cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--task", "Test task", "--agents", "0"])  # Invalid
        assert result.exit_code == 1

    @patch("cli.asyncio.run")
    @patch("cli.console")
    def test_run_command_invalid_rounds(self, mock_console, mock_run):
        """Test run command with invalid rounds."""
        from click.testing import CliRunner
        from cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli, ["run", "--task", "Test task", "--rounds", "25"]  # Exceeds maximum
        )
        assert result.exit_code == 1


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
class TestAPIHelpers:
    """Test API helper functions."""

    def test_create_llm_provider_ollama(self):
        """Test creating Ollama provider."""
        from api_server import create_llm_provider

        provider = create_llm_provider("ollama", "llama3.2", 0.7)
        assert provider is not None

    def test_create_llm_provider_litellm(self):
        """Test creating LiteLLM provider."""
        from api_server import create_llm_provider

        provider = create_llm_provider("openai", "gpt-4", 0.8)
        assert provider is not None

    def test_create_llm_provider_invalid(self):
        """Test creating invalid provider."""
        from api_server import create_llm_provider

        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            create_llm_provider("invalid", "model", 0.7)


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
class TestStreamingAPI:
    """Test streaming API functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api_server import app

        return TestClient(app)

    @patch("api_server.create_llm_provider")
    @patch("agentmind.AgentMind.collaborate")
    def test_streaming_endpoint(self, mock_collaborate, mock_provider, client):
        """Test streaming collaboration endpoint."""
        # Setup mocks
        mock_provider.return_value = MockLLMProvider()
        mock_collaborate.return_value = "Mock result"

        request_data = {
            "task": "Test task",
            "agents": [{"name": "Agent1", "role": "assistant"}],
            "max_rounds": 1,
            "stream": True,
        }

        response = client.post("/collaborate/stream", json=request_data)
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
class TestConcurrency:
    """Test concurrent API requests."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api_server import app

        return TestClient(app)

    @patch("api_server.create_llm_provider")
    @patch("agentmind.AgentMind.collaborate")
    def test_concurrent_collaborations(self, mock_collaborate, mock_provider, client):
        """Test handling multiple concurrent collaborations."""
        # Setup mocks
        mock_provider.return_value = MockLLMProvider()
        mock_collaborate.return_value = "Mock result"

        request_data = {
            "task": "Test task",
            "agents": [{"name": "Agent1", "role": "assistant"}],
            "max_rounds": 1,
        }

        # Send multiple requests
        responses = []
        for _ in range(3):
            response = client.post("/collaborate", json=request_data)
            responses.append(response)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # All should have unique session IDs
        session_ids = [r.json()["session_id"] for r in responses]
        assert len(set(session_ids)) == 3


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
class TestErrorHandling:
    """Test error handling in API and CLI."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api_server import app

        return TestClient(app)

    @patch("api_server.create_llm_provider")
    @patch("agentmind.AgentMind.collaborate")
    def test_collaboration_error_handling(self, mock_collaborate, mock_provider, client):
        """Test error handling during collaboration."""
        # Setup mocks to raise error
        mock_provider.return_value = MockLLMProvider()
        mock_collaborate.side_effect = Exception("Collaboration failed")

        request_data = {
            "task": "Test task",
            "agents": [{"name": "Agent1", "role": "assistant"}],
            "max_rounds": 1,
        }

        response = client.post("/collaborate", json=request_data)
        assert response.status_code == 500


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
class TestTracing:
    """Test tracing functionality in API."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api_server import app

        return TestClient(app)

    @patch("api_server.create_llm_provider")
    @patch("agentmind.AgentMind.collaborate")
    @patch("api_server.Tracer")
    def test_tracing_enabled(self, mock_tracer_class, mock_collaborate, mock_provider, client):
        """Test collaboration with tracing enabled."""
        # Setup mocks
        mock_provider.return_value = MockLLMProvider()
        mock_collaborate.return_value = "Mock result"
        mock_tracer = Mock()
        mock_tracer.get_summary.return_value = {
            "token_usage": {"total_tokens": 100},
            "cost_estimate": {"total_cost": 0.001},
        }
        mock_tracer_class.return_value = mock_tracer

        request_data = {
            "task": "Test task",
            "agents": [{"name": "Agent1", "role": "assistant"}],
            "max_rounds": 1,
            "enable_tracing": True,
        }

        response = client.post("/collaborate", json=request_data)
        assert response.status_code == 200

        # Verify tracer was used
        mock_tracer.start.assert_called_once()
        mock_tracer.end.assert_called_once()

    @patch("api_server.create_llm_provider")
    @patch("agentmind.AgentMind.collaborate")
    def test_tracing_disabled(self, mock_collaborate, mock_provider, client):
        """Test collaboration with tracing disabled."""
        # Setup mocks
        mock_provider.return_value = MockLLMProvider()
        mock_collaborate.return_value = "Mock result"

        request_data = {
            "task": "Test task",
            "agents": [{"name": "Agent1", "role": "assistant"}],
            "max_rounds": 1,
            "enable_tracing": False,
        }

        response = client.post("/collaborate", json=request_data)
        assert response.status_code == 200


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
class TestPerformance:
    """Test performance aspects of API."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from api_server import app

        return TestClient(app)

    @patch("api_server.create_llm_provider")
    @patch("agentmind.AgentMind.collaborate")
    def test_response_time_tracking(self, mock_collaborate, mock_provider, client):
        """Test that response includes duration."""
        # Setup mocks
        mock_provider.return_value = MockLLMProvider()
        mock_collaborate.return_value = "Mock result"

        request_data = {
            "task": "Test task",
            "agents": [{"name": "Agent1", "role": "assistant"}],
            "max_rounds": 1,
        }

        response = client.post("/collaborate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "duration_ms" in data
        assert data["duration_ms"] > 0

    def test_health_check_performance(self, client):
        """Test health check is fast."""
        import time

        start = time.time()
        response = client.get("/health")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.1  # Should be very fast


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
