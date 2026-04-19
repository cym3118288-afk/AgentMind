"""Advanced orchestration modes for multi-agent collaboration.

This module implements:
- Sequential orchestration
- Hierarchical (3-tier: manager-executor-reviewer)
- Debate/Consensus (multi-agent debate + voting + arbitration)
- Swarm (dynamic agent creation/destruction)
- Graph-based (LangGraph compatible)
"""

from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
import asyncio
from abc import ABC, abstractmethod

from ..core.agent import Agent
from ..core.types import Message, MessageRole, CollaborationResult


class OrchestrationMode(str, Enum):
    """Available orchestration modes."""

    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"
    DEBATE = "debate"
    CONSENSUS = "consensus"
    SWARM = "swarm"
    GRAPH = "graph"


class BaseOrchestrator(ABC):
    """Base class for orchestrators."""

    @abstractmethod
    async def orchestrate(
        self,
        agents: List[Agent],
        task: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> CollaborationResult:
        """Orchestrate agent collaboration.

        Args:
            agents: List of agents
            task: Task description
            context: Optional context
            **kwargs: Mode-specific parameters

        Returns:
            Collaboration result
        """
        pass

    @abstractmethod
    def get_mode(self) -> OrchestrationMode:
        """Get orchestration mode."""
        pass


class SequentialOrchestrator(BaseOrchestrator):
    """Sequential orchestration - agents process in order."""

    def get_mode(self) -> OrchestrationMode:
        return OrchestrationMode.SEQUENTIAL

    async def orchestrate(
        self,
        agents: List[Agent],
        task: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> CollaborationResult:
        """Execute agents sequentially.

        Args:
            agents: List of agents
            task: Task description
            context: Optional context
            **kwargs: Additional parameters

        Returns:
            Collaboration result
        """
        if not agents:
            return CollaborationResult(
                success=False,
                error="No agents provided",
                total_rounds=0,
                total_messages=0,
            )

        print(f"[Sequential] Starting with {len(agents)} agents")

        messages = []
        current_message = Message(
            content=task,
            sender="system",
            role=MessageRole.SYSTEM,
        )

        agent_contributions = {agent.name: 0 for agent in agents}

        # Process each agent in sequence
        for i, agent in enumerate(agents):
            print(f"[Sequential] Step {i+1}/{len(agents)}: {agent.name}")

            response = await agent.process_message(current_message)
            if response:
                messages.append(response)
                agent_contributions[agent.name] += 1
                current_message = response

        # Generate final output
        final_output = messages[-1].content if messages else "No output generated"

        return CollaborationResult(
            success=True,
            total_rounds=len(agents),
            total_messages=len(messages),
            final_output=final_output,
            agent_contributions=agent_contributions,
        )


class HierarchicalOrchestrator(BaseOrchestrator):
    """Hierarchical orchestration - 3-tier: manager, executors, reviewer."""

    def get_mode(self) -> OrchestrationMode:
        return OrchestrationMode.HIERARCHICAL

    async def orchestrate(
        self,
        agents: List[Agent],
        task: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> CollaborationResult:
        """Execute in hierarchical mode.

        Args:
            agents: List of agents (first is manager, last is reviewer)
            task: Task description
            context: Optional context
            **kwargs: Additional parameters

        Returns:
            Collaboration result
        """
        if len(agents) < 3:
            return CollaborationResult(
                success=False,
                error="Hierarchical mode requires at least 3 agents",
                total_rounds=0,
                total_messages=0,
            )

        print(f"[Hierarchical] 3-tier orchestration with {len(agents)} agents")

        manager = agents[0]
        executors = agents[1:-1]
        reviewer = agents[-1]

        messages = []
        agent_contributions = {agent.name: 0 for agent in agents}

        # Phase 1: Manager plans
        print("[Hierarchical] Phase 1: Manager planning")
        manager_msg = Message(content=task, sender="system", role=MessageRole.SYSTEM)
        manager_response = await manager.process_message(manager_msg)

        if manager_response:
            messages.append(manager_response)
            agent_contributions[manager.name] += 1

        # Phase 2: Executors work in parallel
        print(f"[Hierarchical] Phase 2: {len(executors)} executors working")
        executor_tasks = [
            executor.process_message(manager_response or manager_msg) for executor in executors
        ]
        executor_responses = await asyncio.gather(*executor_tasks)

        for response in executor_responses:
            if response:
                messages.append(response)
                agent_contributions[response.sender] += 1

        # Phase 3: Reviewer synthesizes
        print("[Hierarchical] Phase 3: Reviewer synthesizing")
        review_content = f"Review these results: {[r.content for r in executor_responses if r]}"
        review_msg = Message(content=review_content, sender="system", role=MessageRole.SYSTEM)
        review_response = await reviewer.process_message(review_msg)

        if review_response:
            messages.append(review_response)
            agent_contributions[reviewer.name] += 1

        final_output = review_response.content if review_response else "No final output"

        return CollaborationResult(
            success=True,
            total_rounds=3,
            total_messages=len(messages),
            final_output=final_output,
            agent_contributions=agent_contributions,
            metadata={"mode": "hierarchical", "phases": 3},
        )


class DebateOrchestrator(BaseOrchestrator):
    """Debate orchestration - agents debate and vote."""

    def get_mode(self) -> OrchestrationMode:
        return OrchestrationMode.DEBATE

    async def orchestrate(
        self,
        agents: List[Agent],
        task: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> CollaborationResult:
        """Execute debate mode.

        Args:
            agents: List of agents
            task: Task description
            context: Optional context
            **kwargs: debate_rounds, voting_enabled

        Returns:
            Collaboration result
        """
        debate_rounds = kwargs.get("debate_rounds", 3)
        voting_enabled = kwargs.get("voting_enabled", True)

        print(f"[Debate] Starting {debate_rounds} rounds with {len(agents)} agents")

        messages = []
        agent_contributions = {agent.name: 0 for agent in agents}

        # Initial positions
        initial_msg = Message(content=task, sender="system", role=MessageRole.SYSTEM)

        for round_num in range(debate_rounds):
            print(f"[Debate] Round {round_num + 1}/{debate_rounds}")

            # Each agent presents their position
            round_responses = []
            for agent in agents:
                # Include previous round context
                context_msg = (
                    initial_msg
                    if round_num == 0
                    else Message(
                        content=f"{task}\n\nPrevious arguments: {[m.content for m in messages[-len(agents):] if m]}",
                        sender="system",
                        role=MessageRole.SYSTEM,
                    )
                )

                response = await agent.process_message(context_msg)
                if response:
                    round_responses.append(response)
                    messages.append(response)
                    agent_contributions[agent.name] += 1

        # Voting phase
        if voting_enabled:
            print("[Debate] Voting phase")
            votes = await self._conduct_voting(agents, messages)
            winner = max(votes.items(), key=lambda x: x[1])[0] if votes else "tie"
            final_output = f"Debate concluded. Winner: {winner}"
        else:
            final_output = "Debate concluded without voting"

        return CollaborationResult(
            success=True,
            total_rounds=debate_rounds,
            total_messages=len(messages),
            final_output=final_output,
            agent_contributions=agent_contributions,
            metadata={"mode": "debate", "votes": votes if voting_enabled else {}},
        )

    async def _conduct_voting(
        self,
        agents: List[Agent],
        debate_messages: List[Message],
    ) -> Dict[str, int]:
        """Conduct voting among agents.

        Args:
            agents: List of agents
            debate_messages: Messages from debate

        Returns:
            Vote counts per agent
        """
        votes = {agent.name: 0 for agent in agents}

        # Simple voting: each agent votes for the most convincing argument
        for agent in agents:
            # In real implementation, would use LLM to evaluate arguments
            # For now, simple random-like voting based on message count
            if debate_messages:
                voted_for = debate_messages[-1].sender
                if voted_for in votes:
                    votes[voted_for] += 1

        return votes


class SwarmOrchestrator(BaseOrchestrator):
    """Swarm orchestration - dynamic agent creation/destruction."""

    def get_mode(self) -> OrchestrationMode:
        return OrchestrationMode.SWARM

    async def orchestrate(
        self,
        agents: List[Agent],
        task: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> CollaborationResult:
        """Execute swarm mode.

        Args:
            agents: Initial agent pool
            task: Task description
            context: Optional context
            **kwargs: max_agents, complexity_threshold

        Returns:
            Collaboration result
        """
        max_agents = kwargs.get("max_agents", 10)
        complexity_threshold = kwargs.get("complexity_threshold", 100)

        print(f"[Swarm] Starting with {len(agents)} agents (max: {max_agents})")

        # Assess task complexity
        task_complexity = len(task.split())  # Simple heuristic

        # Determine number of agents needed
        agents_needed = min(
            max(len(agents), task_complexity // complexity_threshold + 1),
            max_agents,
        )

        print(f"[Swarm] Task complexity: {task_complexity}, agents needed: {agents_needed}")

        # Use available agents
        active_agents = agents[:agents_needed]

        messages = []
        agent_contributions = {agent.name: 0 for agent in active_agents}

        # Swarm execution - all agents work in parallel
        initial_msg = Message(content=task, sender="system", role=MessageRole.SYSTEM)

        tasks = [agent.process_message(initial_msg) for agent in active_agents]
        responses = await asyncio.gather(*tasks)

        for response in responses:
            if response:
                messages.append(response)
                agent_contributions[response.sender] += 1

        # Synthesize results
        final_output = f"Swarm completed with {len(active_agents)} agents"

        return CollaborationResult(
            success=True,
            total_rounds=1,
            total_messages=len(messages),
            final_output=final_output,
            agent_contributions=agent_contributions,
            metadata={
                "mode": "swarm",
                "agents_used": len(active_agents),
                "task_complexity": task_complexity,
            },
        )


class GraphOrchestrator(BaseOrchestrator):
    """Graph-based orchestration - LangGraph compatible."""

    def get_mode(self) -> OrchestrationMode:
        return OrchestrationMode.GRAPH

    def __init__(self):
        """Initialize graph orchestrator."""
        self.graph: Dict[str, List[str]] = {}
        self.node_agents: Dict[str, Agent] = {}

    def add_node(self, node_id: str, agent: Agent) -> None:
        """Add a node to the graph.

        Args:
            node_id: Node identifier
            agent: Agent for this node
        """
        self.node_agents[node_id] = agent
        if node_id not in self.graph:
            self.graph[node_id] = []

    def add_edge(self, from_node: str, to_node: str) -> None:
        """Add an edge between nodes.

        Args:
            from_node: Source node
            to_node: Target node
        """
        if from_node not in self.graph:
            self.graph[from_node] = []
        self.graph[from_node].append(to_node)

    async def orchestrate(
        self,
        agents: List[Agent],
        task: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> CollaborationResult:
        """Execute graph-based orchestration.

        Args:
            agents: List of agents (used if graph not pre-configured)
            task: Task description
            context: Optional context
            **kwargs: start_node

        Returns:
            Collaboration result
        """
        start_node = kwargs.get("start_node", "start")

        # If graph not configured, create simple linear graph
        if not self.graph:
            for i, agent in enumerate(agents):
                node_id = f"node_{i}"
                self.add_node(node_id, agent)
                if i > 0:
                    self.add_edge(f"node_{i-1}", node_id)
            start_node = "node_0"

        print(f"[Graph] Executing graph with {len(self.node_agents)} nodes")

        messages = []
        agent_contributions = {agent.name: 0 for agent in agents}
        visited = set()

        # Execute graph traversal
        current_message = Message(content=task, sender="system", role=MessageRole.SYSTEM)
        await self._traverse_graph(
            start_node,
            current_message,
            visited,
            messages,
            agent_contributions,
        )

        final_output = messages[-1].content if messages else "No output"

        return CollaborationResult(
            success=True,
            total_rounds=len(visited),
            total_messages=len(messages),
            final_output=final_output,
            agent_contributions=agent_contributions,
            metadata={"mode": "graph", "nodes_visited": len(visited)},
        )

    async def _traverse_graph(
        self,
        node_id: str,
        message: Message,
        visited: set,
        messages: List[Message],
        contributions: Dict[str, int],
    ) -> None:
        """Traverse graph recursively.

        Args:
            node_id: Current node
            message: Current message
            visited: Visited nodes
            messages: Message list
            contributions: Contribution tracking
        """
        if node_id in visited or node_id not in self.node_agents:
            return

        visited.add(node_id)
        agent = self.node_agents[node_id]

        print(f"[Graph] Visiting node: {node_id} (agent: {agent.name})")

        response = await agent.process_message(message)
        if response:
            messages.append(response)
            contributions[agent.name] = contributions.get(agent.name, 0) + 1

            # Visit connected nodes
            for next_node in self.graph.get(node_id, []):
                await self._traverse_graph(
                    next_node,
                    response,
                    visited,
                    messages,
                    contributions,
                )

    def visualize_graph(self) -> str:
        """Generate Mermaid diagram of the graph.

        Returns:
            Mermaid diagram string
        """
        lines = ["graph TD"]

        for node_id, agent in self.node_agents.items():
            lines.append(f"    {node_id}[{agent.name}]")

        for from_node, to_nodes in self.graph.items():
            for to_node in to_nodes:
                lines.append(f"    {from_node} --> {to_node}")

        return "\n".join(lines)


# Factory function
def create_orchestrator(mode: OrchestrationMode) -> BaseOrchestrator:
    """Create an orchestrator by mode.

    Args:
        mode: Orchestration mode

    Returns:
        Orchestrator instance
    """
    orchestrators = {
        OrchestrationMode.SEQUENTIAL: SequentialOrchestrator,
        OrchestrationMode.HIERARCHICAL: HierarchicalOrchestrator,
        OrchestrationMode.DEBATE: DebateOrchestrator,
        OrchestrationMode.SWARM: SwarmOrchestrator,
        OrchestrationMode.GRAPH: GraphOrchestrator,
    }

    orchestrator_class = orchestrators.get(mode)
    if not orchestrator_class:
        raise ValueError(f"Unknown orchestration mode: {mode}")

    return orchestrator_class()
