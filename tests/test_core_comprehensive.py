"""Comprehensive test suite for core modules to achieve 100% coverage.

This module adds tests for all uncovered code paths in agent.py and mind.py.
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentmind import Agent, AgentMind, Message
from agentmind.core.types import (
    AgentConfig,
    AgentRole,
    CollaborationStrategy,
)


class TestAgentToolSystem:
    """Test agent tool execution and management."""

    def test_bind_tools(self) -> None:
        """Test tool binding from config."""
        config = AgentConfig(
            name="test_agent",
            role=AgentRole.ANALYST,
            tools=["calculator", "web_search"],
        )
        agent = Agent(name="test_agent", role="analyst", config=config)
        # Tools should be bound (even if not registered)
        assert isinstance(agent._available_tools, list)

    @pytest.mark.asyncio
    async def test_execute_tool_not_available(self) -> None:
        """Test executing a tool that's not available."""
        agent = Agent(name="test_agent", role="analyst")
        result = await agent.execute_tool("nonexistent_tool", param="value")
        assert result["success"] is False
        assert "not available" in result["error"]

    def test_get_tool_definitions(self) -> None:
        """Test getting tool definitions."""
        agent = Agent(name="test_agent", role="analyst")
        definitions = agent.get_tool_definitions()
        assert isinstance(definitions, list)

    def test_get_system_prompt(self) -> None:
        """Test system prompt generation."""
        config = AgentConfig(
            name="test_agent",
            role=AgentRole.ANALYST,
            backstory="Expert data analyst",
            system_prompt="Custom prompt",
        )
        agent = Agent(name="test_agent", role="analyst", config=config)
        prompt = agent.get_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_get_system_prompt_with_memory(self) -> None:
        """Test system prompt includes memory context."""
        agent = Agent(name="test_agent", role="analyst")
        # Add some messages to memory
        agent.memory.append(Message(content="Test 1", sender="user"))
        agent.memory.append(Message(content="Response 1", sender="test_agent"))

        prompt = agent.get_system_prompt()
        assert isinstance(prompt, str)

    @pytest.mark.asyncio
    async def test_process_tool_calls(self) -> None:
        """Test tool call processing from LLM output."""
        agent = Agent(name="test_agent", role="analyst")

        # Test with no tool calls
        result = await agent._process_tool_calls("Just a regular response")
        assert result == []

        # Test with tool call pattern (even though tool doesn't exist)
        result = await agent._process_tool_calls("TOOL[calculator](x=5,y=10)")
        assert isinstance(result, list)


class TestAgentLLMIntegration:
    """Test agent LLM integration features."""

    @pytest.mark.asyncio
    async def test_think_and_respond_without_llm(self) -> None:
        """Test think_and_respond falls back without LLM."""
        agent = Agent(name="test_agent", role="analyst")
        msg = Message(content="Test message", sender="user")

        response = await agent.think_and_respond(msg)
        assert response is not None
        assert response.sender == "test_agent"

    @pytest.mark.asyncio
    async def test_think_and_respond_with_mock_llm(self) -> None:
        """Test think_and_respond with mocked LLM."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "LLM generated response"
        mock_response.model = "test - model"
        mock_response.usage = {"tokens": 100}
        mock_llm.generate = AsyncMock(return_value=mock_response)

        agent = Agent(name="test_agent", role="analyst", llm_provider=mock_llm)
        msg = Message(content="Test message", sender="user")

        response = await agent.think_and_respond(msg)
        assert response is not None
        assert "LLM generated response" in response.content
        assert response.metadata["model"] == "test - model"

    @pytest.mark.asyncio
    async def test_think_and_respond_tool_use_mode(self) -> None:
        """Test think_and_respond in tool_use mode."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Response with TOOL[calculator](x=5)"
        mock_response.model = "test - model"
        mock_response.usage = {"tokens": 100}
        mock_llm.generate = AsyncMock(return_value=mock_response)

        config = AgentConfig(name="test_agent", role=AgentRole.ANALYST, tools=["calculator"])
        agent = Agent(name="test_agent", role="analyst", config=config, llm_provider=mock_llm)
        msg = Message(content="Calculate something", sender="user")

        response = await agent.think_and_respond(msg, mode="tool_use")
        assert response is not None

    @pytest.mark.asyncio
    async def test_think_and_respond_llm_error(self) -> None:
        """Test think_and_respond handles LLM errors gracefully."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM error"))

        agent = Agent(name="test_agent", role="analyst", llm_provider=mock_llm)
        msg = Message(content="Test message", sender="user")

        # Should fall back to template response
        response = await agent.think_and_respond(msg)
        assert response is not None
        assert response.sender == "test_agent"


class TestAgentMemory:
    """Test agent memory management."""

    def test_get_memory_summary(self) -> None:
        """Test memory summary generation."""
        agent = Agent(name="test_agent", role="analyst")
        summary = agent.get_memory_summary()
        assert "test_agent" in summary
        assert "0 messages" in summary

    def test_activate_deactivate(self) -> None:
        """Test agent activation / deactivation."""
        agent = Agent(name="test_agent", role="analyst")
        assert agent.is_active is True

        agent.deactivate()
        assert agent.is_active is False

        agent.activate()
        assert agent.is_active is True

    def test_agent_repr(self) -> None:
        """Test agent string representations."""
        agent = Agent(name="test_agent", role="analyst")

        repr_str = repr(agent)
        assert "test_agent" in repr_str
        assert "analyst" in repr_str
        assert "active" in repr_str

        str_str = str(agent)
        assert "test_agent" in str_str
        assert "analyst" in str_str


class TestAgentMindStrategies:
    """Test different collaboration strategies."""

    @pytest.mark.asyncio
    async def test_round_robin_strategy(self) -> None:
        """Test round - robin collaboration strategy."""
        mind = AgentMind(strategy=CollaborationStrategy.ROUND_ROBIN)
        agent1 = Agent(name="agent1", role="analyst")
        agent2 = Agent(name="agent2", role="creative")
        mind.add_agent(agent1)
        mind.add_agent(agent2)

        result = await mind.start_collaboration("Test task", max_rounds=3)
        assert result.success is True
        assert result.total_rounds > 0

    @pytest.mark.asyncio
    async def test_round_robin_with_stop_condition(self) -> None:
        """Test round - robin with stop condition."""
        mind = AgentMind(strategy=CollaborationStrategy.ROUND_ROBIN)
        agent1 = Agent(name="agent1", role="analyst")
        mind.add_agent(agent1)

        def stop_condition(messages):
            return len(messages) > 0

        result = await mind.start_collaboration(
            "Test task", max_rounds=5, stop_condition=stop_condition
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_hierarchical_strategy_with_supervisor(self) -> None:
        """Test hierarchical strategy with supervisor."""
        mind = AgentMind(strategy=CollaborationStrategy.HIERARCHICAL)
        supervisor = Agent(name="supervisor", role="supervisor")
        agent1 = Agent(name="agent1", role="analyst")
        agent2 = Agent(name="agent2", role="creative")

        mind.add_agent(supervisor)
        mind.add_agent(agent1)
        mind.add_agent(agent2)

        result = await mind.start_collaboration("Test task")
        assert result.success is True
        assert "supervisor" in result.agent_contributions

    @pytest.mark.asyncio
    async def test_hierarchical_strategy_without_supervisor(self) -> None:
        """Test hierarchical strategy falls back without supervisor."""
        mind = AgentMind(strategy=CollaborationStrategy.HIERARCHICAL)
        agent1 = Agent(name="agent1", role="analyst")
        agent2 = Agent(name="agent2", role="creative")

        mind.add_agent(agent1)
        mind.add_agent(agent2)

        result = await mind.start_collaboration("Test task")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_topic_based_strategy(self) -> None:
        """Test topic - based strategy (defaults to broadcast)."""
        mind = AgentMind(strategy=CollaborationStrategy.TOPIC_BASED)
        agent1 = Agent(name="agent1", role="analyst")
        mind.add_agent(agent1)

        result = await mind.start_collaboration("Test task")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_collaboration_with_stop_condition(self) -> None:
        """Test collaboration with custom stop condition."""
        mind = AgentMind()
        agent1 = Agent(name="agent1", role="analyst")
        mind.add_agent(agent1)

        def stop_condition(messages):
            return len(messages) >= 1

        result = await mind.start_collaboration("Test task", stop_condition=stop_condition)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_collaboration_exception_handling(self) -> None:
        """Test collaboration handles exceptions gracefully."""
        mind = AgentMind()
        agent1 = Agent(name="agent1", role="analyst")
        mind.add_agent(agent1)

        # Mock agent to raise exception
        async def failing_process(msg):
            raise Exception("Test error")

        agent1.process_message = failing_process

        result = await mind.start_collaboration("Test task")
        assert result.success is False
        assert result.error is not None


class TestAgentMindSessionManagement:
    """Test session save / load functionality."""

    def test_save_session(self, tmp_path) -> None:
        """Test saving a session."""
        mind = AgentMind()
        agent = Agent(name="test_agent", role="analyst")
        mind.add_agent(agent)

        session_path = mind.save_session("test_session", save_dir=str(tmp_path))
        assert Path(session_path).exists()

        # Verify session file content
        with open(session_path, "r") as f:
            data = json.load(f)
            assert data["session_id"] == "test_session"
            assert len(data["agents"]) == 1

    def test_load_session(self, tmp_path) -> None:
        """Test loading a session."""
        # Create and save a session
        mind1 = AgentMind()
        agent = Agent(name="test_agent", role="analyst")
        mind1.add_agent(agent)
        mind1.save_session("test_session", save_dir=str(tmp_path))

        # Load session in new AgentMind
        mind2 = AgentMind()
        success = mind2.load_session("test_session", save_dir=str(tmp_path))

        assert success is True
        assert len(mind2.agents) == 1
        assert mind2.agents[0].name == "test_agent"

    def test_load_nonexistent_session(self, tmp_path) -> None:
        """Test loading a nonexistent session."""
        mind = AgentMind()
        success = mind.load_session("nonexistent", save_dir=str(tmp_path))
        assert success is False

    def test_load_session_with_corrupt_data(self, tmp_path) -> None:
        """Test loading a session with corrupt data."""
        # Create corrupt session file
        session_file = tmp_path / "corrupt.json"
        session_file.write_text("invalid json {")

        mind = AgentMind()
        success = mind.load_session("corrupt", save_dir=str(tmp_path))
        assert success is False

    def test_list_sessions(self, tmp_path) -> None:
        """Test listing saved sessions."""
        mind = AgentMind()
        agent = Agent(name="test_agent", role="analyst")
        mind.add_agent(agent)

        # Save multiple sessions
        mind.save_session("session1", save_dir=str(tmp_path))
        mind.save_session("session2", save_dir=str(tmp_path))

        sessions = mind.list_sessions(save_dir=str(tmp_path))
        assert len(sessions) >= 2
        assert any(s["session_id"] == "session1" for s in sessions)
        assert any(s["session_id"] == "session2" for s in sessions)

    def test_list_sessions_empty_dir(self, tmp_path) -> None:
        """Test listing sessions in empty directory."""
        empty_dir = tmp_path / "empty"
        mind = AgentMind()
        sessions = mind.list_sessions(save_dir=str(empty_dir))
        assert sessions == []


class TestAgentMindUtilities:
    """Test AgentMind utility methods."""

    def test_clear_history(self) -> None:
        """Test clearing conversation history."""
        mind = AgentMind()
        mind.conversation_history.append(Message(content="Test", sender="system"))
        assert len(mind.conversation_history) > 0

        mind.clear_history()
        assert len(mind.conversation_history) == 0

    def test_agentmind_repr(self) -> None:
        """Test AgentMind string representations."""
        mind = AgentMind()
        agent = Agent(name="test_agent", role="analyst")
        mind.add_agent(agent)

        repr_str = repr(mind)
        assert "AgentMind" in repr_str
        assert "agents=1" in repr_str

        str_str = str(mind)
        assert "1 agents" in str_str

    def test_generate_final_output_empty(self) -> None:
        """Test final output generation with no responses."""
        mind = AgentMind()
        output = mind._generate_final_output([])
        assert "No responses" in output

    def test_generate_final_output_with_responses(self) -> None:
        """Test final output generation with responses."""
        mind = AgentMind()
        responses = [
            Message(content="Response 1", sender="agent1"),
            Message(content="Response 2", sender="agent2"),
        ]
        output = mind._generate_final_output(responses)
        assert "agent1" in output
        assert "agent2" in output
        assert "Response 1" in output

    @pytest.mark.asyncio
    async def test_broadcast_exclude_sender(self) -> None:
        """Test broadcast with sender exclusion."""
        mind = AgentMind()
        agent1 = Agent(name="agent1", role="analyst")
        agent2 = Agent(name="agent2", role="creative")
        mind.add_agent(agent1)
        mind.add_agent(agent2)

        msg = Message(content="Test", sender="agent1")
        responses = await mind.broadcast_message(msg, exclude_sender=True)

        # Only agent2 should respond
        assert len(responses) == 1
        assert responses[0].sender == "agent2"

    @pytest.mark.asyncio
    async def test_broadcast_without_llm(self) -> None:
        """Test broadcast without LLM."""
        mind = AgentMind()
        agent1 = Agent(name="agent1", role="analyst")
        mind.add_agent(agent1)

        msg = Message(content="Test", sender="system")
        responses = await mind.broadcast_message(msg, use_llm=False)

        assert len(responses) == 1

    @pytest.mark.asyncio
    async def test_broadcast_with_llm(self) -> None:
        """Test broadcast with LLM."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "LLM response"
        mock_response.model = "test - model"
        mock_response.usage = {"tokens": 100}
        mock_llm.generate = AsyncMock(return_value=mock_response)

        mind = AgentMind(llm_provider=mock_llm)
        agent1 = Agent(name="agent1", role="analyst", llm_provider=mock_llm)
        mind.add_agent(agent1)

        msg = Message(content="Test", sender="system")
        responses = await mind.broadcast_message(msg, use_llm=True)

        assert len(responses) == 1


class TestAgentMindLLMProvider:
    """Test AgentMind LLM provider propagation."""

    def test_llm_provider_propagation(self) -> None:
        """Test that LLM provider is propagated to agents."""
        mock_llm = MagicMock()
        mind = AgentMind(llm_provider=mock_llm)

        agent = Agent(name="test_agent", role="analyst")
        mind.add_agent(agent)

        assert agent.llm_provider is mock_llm

    def test_llm_provider_not_overridden(self) -> None:
        """Test that existing LLM provider is not overridden."""
        mock_llm1 = MagicMock()
        mock_llm2 = MagicMock()

        mind = AgentMind(llm_provider=mock_llm1)
        agent = Agent(name="test_agent", role="analyst", llm_provider=mock_llm2)
        mind.add_agent(agent)

        # Agent should keep its own LLM provider
        assert agent.llm_provider is mock_llm2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
