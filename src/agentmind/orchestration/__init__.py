"""Advanced orchestration strategies for multi-agent collaboration.

This module provides sophisticated orchestration patterns beyond simple
broadcasting, including hierarchical, round-robin, and topic-based routing.

Available orchestration modes:
- Sequential: Chain of responsibility with context passing
- Hierarchical: 3-tier architecture (manager, workers, reviewer)
- Debate: Multi-round deliberation with voting
- Consensus: Agreement-based decision making
- Swarm: Dynamic scaling with load balancing
- Graph: DAG-based workflows
- Hybrid: Combinations of multiple modes
"""

from abc import ABC, abstractmethod
from typing import List

from ..core.agent import Agent
from ..core.types import Message

# Import advanced modes
from .advanced_modes import (
    OrchestrationMode,
    OrchestrationMetrics,
    BaseOrchestrator,
    SequentialOrchestrator,
    HierarchicalOrchestrator,
    DebateOrchestrator,
    ConsensusOrchestrator,
    SwarmOrchestrator,
    GraphOrchestrator,
    HybridOrchestrator,
    create_orchestrator,
    get_available_modes,
    get_mode_description,
    recommend_mode,
)


class OrchestrationStrategy(ABC):
    """Abstract base class for orchestration strategies.

    Orchestration strategies determine how messages are routed between agents.
    """

    @abstractmethod
    async def route_message(
        self, message: Message, agents: List[Agent], sender: str
    ) -> List[Agent]:
        """Determine which agents should receive a message.

        Args:
            message: The message to route
            agents: All available agents
            sender: Name of the sending agent

        Returns:
            List of agents that should receive the message

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement route_message()")


class BroadcastStrategy(OrchestrationStrategy):
    """Broadcast messages to all agents (default strategy)."""

    async def route_message(
        self, message: Message, agents: List[Agent], sender: str
    ) -> List[Agent]:
        """Route to all agents except sender."""
        return [agent for agent in agents if agent.name != sender]


class RoundRobinStrategy(OrchestrationStrategy):
    """Route messages to agents in round-robin fashion.

    To be fully implemented in Phase 2.
    """

    async def route_message(
        self, message: Message, agents: List[Agent], sender: str
    ) -> List[Agent]:
        """Route to next agent in sequence."""
        raise NotImplementedError("Round-robin strategy coming in Phase 2")


class HierarchicalStrategy(OrchestrationStrategy):
    """Hierarchical routing with supervisor and sub-agents.

    To be implemented in Phase 2.
    """

    async def route_message(
        self, message: Message, agents: List[Agent], sender: str
    ) -> List[Agent]:
        """Route based on hierarchy."""
        raise NotImplementedError("Hierarchical strategy coming in Phase 2")


class TopicBasedStrategy(OrchestrationStrategy):
    """Route messages based on topic/metadata matching.

    To be implemented in Phase 2.
    """

    async def route_message(
        self, message: Message, agents: List[Agent], sender: str
    ) -> List[Agent]:
        """Route based on message topic."""
        raise NotImplementedError("Topic-based strategy coming in Phase 2")


__all__ = [
    # Strategies
    "OrchestrationStrategy",
    "BroadcastStrategy",
    "RoundRobinStrategy",
    "HierarchicalStrategy",
    "TopicBasedStrategy",
    # Advanced modes
    "OrchestrationMode",
    "OrchestrationMetrics",
    "BaseOrchestrator",
    "SequentialOrchestrator",
    "HierarchicalOrchestrator",
    "DebateOrchestrator",
    "ConsensusOrchestrator",
    "SwarmOrchestrator",
    "GraphOrchestrator",
    "HybridOrchestrator",
    "create_orchestrator",
    "get_available_modes",
    "get_mode_description",
    "recommend_mode",
]
