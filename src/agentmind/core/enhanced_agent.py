"""Enhanced Agent class with multi-modal support and advanced features.

This module extends the base Agent with:
- Multi-modal support (image, audio, video)
- Human-in-the-loop hooks
- Dynamic role switching
- Sub-agent management
"""

from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum
import asyncio

from .agent import Agent as BaseAgent
from .types import Message, MessageRole, AgentConfig
from ..llm.provider import LLMProvider
from ..tools import ToolRegistry


class AgentState(str, Enum):
    """Agent execution states."""

    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_HUMAN = "waiting_human"
    DELEGATING = "delegating"
    ERROR = "error"


class MultiModalMessage(Message):
    """Extended message with multi-modal support."""

    image_data: Optional[bytes] = None
    audio_data: Optional[bytes] = None
    video_data: Optional[bytes] = None
    file_attachments: List[Dict[str, Any]] = []
    embeddings: Optional[List[float]] = None

    class Config:
        arbitrary_types_allowed = True


class EnhancedAgent(BaseAgent):
    """Enhanced Agent with advanced capabilities."""

    def __init__(
        self,
        name: str,
        role: str = "assistant",
        config: Optional[AgentConfig] = None,
        llm_provider: Optional[LLMProvider] = None,
        tool_registry: Optional[ToolRegistry] = None,
        human_in_loop: bool = False,
        human_callback: Optional[Callable] = None,
    ) -> None:
        """Initialize enhanced agent.

        Args:
            name: Agent name
            role: Agent role
            config: Agent configuration
            llm_provider: LLM provider
            tool_registry: Tool registry
            human_in_loop: Enable human-in-the-loop
            human_callback: Callback for human input
        """
        super().__init__(name, role, config, llm_provider, tool_registry)

        self.state = AgentState.IDLE
        self.human_in_loop = human_in_loop
        self.human_callback = human_callback
        self.sub_agents: List[BaseAgent] = []
        self.parent_agent: Optional[BaseAgent] = None
        self.execution_history: List[Dict[str, Any]] = []

    async def process_multimodal_message(
        self,
        message: Union[Message, MultiModalMessage],
    ) -> Optional[Message]:
        """Process a multi-modal message.

        Args:
            message: Message with potential multi-modal content

        Returns:
            Response message
        """
        self.state = AgentState.THINKING

        try:
            # Check if human approval needed
            if self.human_in_loop and self.human_callback:
                approved = await self._request_human_approval(message)
                if not approved:
                    self.state = AgentState.IDLE
                    return Message(
                        content="Action rejected by human",
                        sender=self.name,
                        role=MessageRole.AGENT,
                    )

            # Process based on content type
            if isinstance(message, MultiModalMessage):
                response = await self._process_multimodal(message)
            else:
                response = await self.think_and_respond(message)

            self.state = AgentState.IDLE
            return response

        except Exception as e:
            self.state = AgentState.ERROR
            return Message(
                content=f"Error processing message: {str(e)}",
                sender=self.name,
                role=MessageRole.AGENT,
                metadata={"error": str(e)},
            )

    async def _process_multimodal(self, message: MultiModalMessage) -> Message:
        """Process multi-modal content.

        Args:
            message: Multi-modal message

        Returns:
            Response message
        """
        # Extract content types
        content_parts = [message.content]

        if message.image_data:
            content_parts.append("[Image attached]")
        if message.audio_data:
            content_parts.append("[Audio attached]")
        if message.video_data:
            content_parts.append("[Video attached]")
        if message.file_attachments:
            content_parts.append(f"[{len(message.file_attachments)} files attached]")

        # Create combined message
        combined_content = " ".join(content_parts)
        text_message = Message(
            content=combined_content,
            sender=message.sender,
            role=message.role,
            metadata=message.metadata,
        )

        return await self.think_and_respond(text_message)

    async def _request_human_approval(self, message: Message) -> bool:
        """Request human approval for an action.

        Args:
            message: Message to approve

        Returns:
            True if approved
        """
        if not self.human_callback:
            return True

        self.state = AgentState.WAITING_HUMAN

        try:
            # Call human callback
            if asyncio.iscoroutinefunction(self.human_callback):
                approved = await self.human_callback(self.name, message)
            else:
                approved = self.human_callback(self.name, message)

            return bool(approved)
        except Exception as e:
            print(f"[!] Human callback error: {e}")
            return False

    def switch_role(self, new_role: str, new_config: Optional[AgentConfig] = None) -> None:
        """Dynamically switch agent role.

        Args:
            new_role: New role to adopt
            new_config: Optional new configuration
        """
        old_role = self.role
        self.role = new_role

        if new_config:
            self.config = new_config
        else:
            # Update role in existing config
            self.config.role = new_role

        print(f"[*] Agent {self.name} switched role: {old_role} -> {new_role}")

        # Record in history
        self.execution_history.append(
            {
                "action": "role_switch",
                "old_role": old_role,
                "new_role": new_role,
            }
        )

    def add_sub_agent(self, agent: BaseAgent) -> None:
        """Add a sub-agent.

        Args:
            agent: Sub-agent to add
        """
        self.sub_agents.append(agent)
        if isinstance(agent, EnhancedAgent):
            agent.parent_agent = self
        print(f"[+] Agent {self.name} added sub-agent: {agent.name}")

    def remove_sub_agent(self, agent_name: str) -> bool:
        """Remove a sub-agent.

        Args:
            agent_name: Name of sub-agent to remove

        Returns:
            True if removed
        """
        for i, agent in enumerate(self.sub_agents):
            if agent.name == agent_name:
                self.sub_agents.pop(i)
                if isinstance(agent, EnhancedAgent):
                    agent.parent_agent = None
                print(f"[-] Agent {self.name} removed sub-agent: {agent_name}")
                return True
        return False

    async def delegate_to_sub_agent(
        self,
        sub_agent_name: str,
        task: Message,
    ) -> Optional[Message]:
        """Delegate a task to a sub-agent.

        Args:
            sub_agent_name: Name of sub-agent
            task: Task message

        Returns:
            Sub-agent response
        """
        self.state = AgentState.DELEGATING

        # Find sub-agent
        sub_agent = None
        for agent in self.sub_agents:
            if agent.name == sub_agent_name:
                sub_agent = agent
                break

        if not sub_agent:
            print(f"[!] Sub-agent not found: {sub_agent_name}")
            self.state = AgentState.IDLE
            return None

        # Delegate task
        print(f"[*] Agent {self.name} delegating to {sub_agent_name}")

        if isinstance(sub_agent, EnhancedAgent):
            response = await sub_agent.process_multimodal_message(task)
        else:
            response = await sub_agent.process_message(task)

        self.state = AgentState.IDLE

        # Record in history
        self.execution_history.append(
            {
                "action": "delegation",
                "sub_agent": sub_agent_name,
                "task": task.content,
                "response": response.content if response else None,
            }
        )

        return response

    async def broadcast_to_sub_agents(self, message: Message) -> List[Message]:
        """Broadcast a message to all sub-agents.

        Args:
            message: Message to broadcast

        Returns:
            List of responses
        """
        if not self.sub_agents:
            return []

        self.state = AgentState.DELEGATING
        print(f"[*] Agent {self.name} broadcasting to {len(self.sub_agents)} sub-agents")

        # Process in parallel
        tasks = []
        for agent in self.sub_agents:
            if isinstance(agent, EnhancedAgent):
                tasks.append(agent.process_multimodal_message(message))
            else:
                tasks.append(agent.process_message(message))

        responses = await asyncio.gather(*tasks)
        self.state = AgentState.IDLE

        return [r for r in responses if r is not None]

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary.

        Returns:
            Summary dict
        """
        return {
            "name": self.name,
            "role": self.role,
            "state": self.state.value,
            "memory_size": len(self.memory),
            "sub_agents": [a.name for a in self.sub_agents],
            "parent": self.parent_agent.name if self.parent_agent else None,
            "execution_history": len(self.execution_history),
            "human_in_loop": self.human_in_loop,
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"EnhancedAgent(name='{self.name}', role='{self.role}', "
            f"state={self.state.value}, sub_agents={len(self.sub_agents)})"
        )
