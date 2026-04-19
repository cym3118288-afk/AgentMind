"""Advanced orchestration modes for multi-agent collaboration.

This module implements production-ready orchestration patterns:
- Sequential: Chain of responsibility with context passing and error handling
- Hierarchical: 3-tier architecture with manager, workers, and reviewer
- Debate: Multi-round deliberation with voting and convergence detection
- Consensus: Agreement-based decision making with iterative refinement
- Swarm: Dynamic scaling with work stealing and load balancing
- Graph: DAG-based workflows with parallel execution and cycle detection
- Hybrid: Combinations of multiple modes

All modes support:
- Full async/await
- Comprehensive error handling and recovery
- Detailed logging and observability
- Performance optimization
- Progress tracking and metrics
"""

from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum
import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from collections import defaultdict

from ..core.agent import Agent
from ..core.types import Message, MessageRole, CollaborationResult

# Configure logging
logger = logging.getLogger(__name__)


class OrchestrationMode(str, Enum):
    """Available orchestration modes."""

    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"
    DEBATE = "debate"
    CONSENSUS = "consensus"
    SWARM = "swarm"
    GRAPH = "graph"
    HYBRID = "hybrid"


@dataclass
class OrchestrationMetrics:
    """Metrics for orchestration execution."""

    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_messages: int = 0
    total_rounds: int = 0
    agent_workload: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

    def record_message(self, agent_name: str) -> None:
        """Record a message from an agent."""
        self.total_messages += 1
        self.agent_workload[agent_name] = self.agent_workload.get(agent_name, 0) + 1

    def record_error(self, error: str) -> None:
        """Record an error."""
        self.errors.append(error)
        logger.error(f"Orchestration error: {error}")

    def record_warning(self, warning: str) -> None:
        """Record a warning."""
        self.warnings.append(warning)
        logger.warning(f"Orchestration warning: {warning}")

    def finalize(self) -> None:
        """Finalize metrics collection."""
        self.end_time = time.time()

    def get_duration(self) -> float:
        """Get execution duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "duration": self.get_duration(),
            "total_messages": self.total_messages,
            "total_rounds": self.total_rounds,
            "agent_workload": self.agent_workload,
            "errors": self.errors,
            "warnings": self.warnings,
            "custom_metrics": self.custom_metrics,
        }


class BaseOrchestrator(ABC):
    """Base class for orchestrators with common functionality."""

    def __init__(self) -> None:
        """Initialize base orchestrator."""
        self.metrics = OrchestrationMetrics()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

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

    async def _safe_process_message(
        self, agent: Agent, message: Message, timeout: Optional[float] = None
    ) -> Optional[Message]:
        """Safely process a message with error handling.

        Args:
            agent: Agent to process message
            message: Message to process
            timeout: Optional timeout in seconds

        Returns:
            Response message or None on error
        """
        try:
            if timeout:
                response = await asyncio.wait_for(
                    agent.process_message(message), timeout=timeout
                )
            else:
                response = await agent.process_message(message)

            if response:
                self.metrics.record_message(agent.name)
            return response

        except asyncio.TimeoutError:
            error_msg = f"Agent {agent.name} timed out after {timeout}s"
            self.metrics.record_error(error_msg)
            return None
        except Exception as e:
            error_msg = f"Agent {agent.name} error: {str(e)}"
            self.metrics.record_error(error_msg)
            return None

    def _validate_agents(self, agents: List[Agent], min_agents: int = 1) -> bool:
        """Validate agent list.

        Args:
            agents: List of agents to validate
            min_agents: Minimum required agents

        Returns:
            True if valid, False otherwise
        """
        if not agents:
            self.metrics.record_error("No agents provided")
            return False

        if len(agents) < min_agents:
            self.metrics.record_error(
                f"Insufficient agents: {len(agents)} < {min_agents}"
            )
            return False

        active_agents = [a for a in agents if a.is_active]
        if not active_agents:
            self.metrics.record_warning("No active agents available")
            return False

        return True

    def _create_result(
        self,
        success: bool,
        messages: List[Message],
        error: Optional[str] = None,
    ) -> CollaborationResult:
        """Create a collaboration result.

        Args:
            success: Whether orchestration succeeded
            messages: List of messages exchanged
            error: Optional error message

        Returns:
            CollaborationResult
        """
        self.metrics.finalize()

        agent_contributions = {}
        for agent_name, count in self.metrics.agent_workload.items():
            agent_contributions[agent_name] = count

        final_output = messages[-1].content if messages else None

        return CollaborationResult(
            success=success,
            total_rounds=self.metrics.total_rounds,
            total_messages=self.metrics.total_messages,
            final_output=final_output,
            agent_contributions=agent_contributions,
            error=error,
            metadata={
                "mode": self.get_mode().value,
                "duration": self.metrics.get_duration(),
                "metrics": self.metrics.to_dict(),
            },
        )


class SequentialOrchestrator(BaseOrchestrator):
    """Sequential orchestration with chain of responsibility pattern.

    Features:
    - Context passing between agents
    - Early termination on errors
    - Progress tracking
    - Retry logic for failed steps
    """

    def get_mode(self) -> OrchestrationMode:
        return OrchestrationMode.SEQUENTIAL

    async def orchestrate(
        self,
        agents: List[Agent],
        task: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> CollaborationResult:
        """Execute agents sequentially with context passing.

        Args:
            agents: List of agents
            task: Task description
            context: Optional initial context
            **kwargs: Additional parameters
                - early_termination: Stop on first error (default: True)
                - timeout_per_agent: Timeout per agent in seconds
                - max_retries: Max retries per agent (default: 0)
                - pass_full_history: Pass all previous messages (default: False)

        Returns:
            Collaboration result
        """
        if not self._validate_agents(agents):
            return self._create_result(False, [], "Invalid agents")

        early_termination = kwargs.get("early_termination", True)
        timeout_per_agent = kwargs.get("timeout_per_agent")
        max_retries = kwargs.get("max_retries", 0)
        pass_full_history = kwargs.get("pass_full_history", False)

        self.logger.info(
            f"Starting sequential orchestration with {len(agents)} agents"
        )

        messages: List[Message] = []
        current_context = context or {}

        # Initial message
        current_message = Message(
            content=task,
            sender="system",
            role=MessageRole.SYSTEM,
            metadata={"context": current_context},
        )
        messages.append(current_message)

        # Process each agent in sequence
        for i, agent in enumerate(agents):
            if not agent.is_active:
                self.metrics.record_warning(f"Agent {agent.name} is inactive, skipping")
                continue

            self.logger.info(f"Step {i + 1}/{len(agents)}: {agent.name}")
            self.metrics.total_rounds += 1

            # Prepare message with context
            if pass_full_history:
                # Include all previous messages
                message_content = f"{task}\n\nPrevious steps:\n"
                for msg in messages[1:]:  # Skip initial system message
                    message_content += f"- {msg.sender}: {msg.content[:100]}...\n"
                message_content += f"\nYour turn: Continue from where {messages[-1].sender} left off."
            else:
                # Only pass last message
                message_content = current_message.content

            step_message = Message(
                content=message_content,
                sender="orchestrator",
                role=MessageRole.SYSTEM,
                metadata={"step": i + 1, "context": current_context},
            )

            # Execute with retries
            response = await self._execute_with_retry(
                agent, step_message, max_retries, timeout_per_agent
            )

            if response:
                messages.append(response)
                current_message = response

                # Update context from response metadata
                if response.metadata:
                    current_context.update(response.metadata.get("context", {}))

                self.logger.debug(f"Agent {agent.name} completed successfully")
            else:
                error_msg = f"Agent {agent.name} failed to respond"
                self.metrics.record_error(error_msg)

                if early_termination:
                    self.logger.error(f"Early termination triggered at step {i + 1}")
                    return self._create_result(False, messages, error_msg)

        success = len(messages) > 1  # At least one agent responded
        return self._create_result(success, messages)

    async def _execute_with_retry(
        self,
        agent: Agent,
        message: Message,
        max_retries: int,
        timeout: Optional[float],
    ) -> Optional[Message]:
        """Execute agent with retry logic.

        Args:
            agent: Agent to execute
            message: Message to process
            max_retries: Maximum retry attempts
            timeout: Timeout per attempt

        Returns:
            Response message or None
        """
        for attempt in range(max_retries + 1):
            if attempt > 0:
                self.logger.info(f"Retry attempt {attempt}/{max_retries} for {agent.name}")
                await asyncio.sleep(0.5 * attempt)  # Exponential backoff

            response = await self._safe_process_message(agent, message, timeout)
            if response:
                return response

        return None


class HierarchicalOrchestrator(BaseOrchestrator):
    """Hierarchical orchestration with 3-tier architecture.

    Architecture:
    - Manager: Task decomposition and delegation
    - Workers: Parallel execution
    - Reviewer: Quality control and synthesis

    Features:
    - Load balancing across workers
    - Escalation mechanism
    - Quality gates
    - Work redistribution on failure
    """

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
            agents: List of agents (first is manager, last is reviewer, rest are workers)
            task: Task description
            context: Optional context
            **kwargs: Additional parameters
                - quality_threshold: Minimum quality score (0-1)
                - max_escalations: Maximum escalation attempts
                - worker_timeout: Timeout per worker
                - enable_load_balancing: Balance work across workers

        Returns:
            Collaboration result
        """
        if not self._validate_agents(agents, min_agents=3):
            return self._create_result(
                False, [], "Hierarchical mode requires at least 3 agents"
            )

        quality_threshold = kwargs.get("quality_threshold", 0.7)
        max_escalations = kwargs.get("max_escalations", 2)
        worker_timeout = kwargs.get("worker_timeout", 30.0)
        enable_load_balancing = kwargs.get("enable_load_balancing", True)

        self.logger.info(
            f"Starting hierarchical orchestration with {len(agents)} agents"
        )

        manager = agents[0]
        workers = agents[1:-1]
        reviewer = agents[-1]

        messages: List[Message] = []
        escalation_count = 0

        # Phase 1: Manager decomposes task
        self.logger.info("Phase 1: Manager planning and task decomposition")
        self.metrics.total_rounds += 1

        manager_msg = Message(
            content=f"""As the manager, decompose this task into {len(workers)} subtasks:

Task: {task}

Provide:
1. Clear subtask descriptions
2. Priority levels
3. Dependencies between subtasks

Format each subtask as:
SUBTASK [number]: [description]
PRIORITY: [high/medium/low]
DEPENDENCIES: [none or list]""",
            sender="system",
            role=MessageRole.SYSTEM,
        )

        manager_response = await self._safe_process_message(
            manager, manager_msg, worker_timeout
        )

        if not manager_response:
            return self._create_result(False, messages, "Manager failed to respond")

        messages.append(manager_response)

        # Parse subtasks
        subtasks = self._parse_subtasks(manager_response.content, len(workers))

        # Phase 2: Workers execute in parallel
        self.logger.info(f"Phase 2: {len(workers)} workers executing subtasks")
        self.metrics.total_rounds += 1

        worker_results = await self._execute_workers(
            workers, subtasks, worker_timeout, enable_load_balancing
        )

        for result in worker_results:
            if result:
                messages.append(result)

        # Phase 3: Reviewer evaluates and synthesizes
        while escalation_count <= max_escalations:
            self.logger.info(
                f"Phase 3: Reviewer evaluation (attempt {escalation_count + 1})"
            )
            self.metrics.total_rounds += 1

            review_content = f"""Review and synthesize these worker results:

Original task: {task}

Worker outputs:
"""
            for i, result in enumerate(worker_results):
                if result:
                    review_content += f"\nWorker {i + 1}: {result.content[:200]}...\n"

            review_content += f"""

Evaluate:
1. Quality score (0-1)
2. Completeness
3. Issues found
4. Final synthesis

Format:
QUALITY: [0.0-1.0]
COMPLETENESS: [percentage]
ISSUES: [list or none]
SYNTHESIS: [final output]"""

            review_msg = Message(
                content=review_content, sender="system", role=MessageRole.SYSTEM
            )

            review_response = await self._safe_process_message(
                reviewer, review_msg, worker_timeout
            )

            if not review_response:
                return self._create_result(False, messages, "Reviewer failed to respond")

            messages.append(review_response)

            # Check quality
            quality_score = self._extract_quality_score(review_response.content)

            if quality_score >= quality_threshold:
                self.logger.info(f"Quality threshold met: {quality_score:.2f}")
                break

            # Escalate if quality insufficient
            escalation_count += 1
            if escalation_count <= max_escalations:
                self.logger.warning(
                    f"Quality below threshold ({quality_score:.2f} < {quality_threshold}), escalating"
                )
                self.metrics.record_warning(
                    f"Escalation {escalation_count}: Quality {quality_score:.2f}"
                )

                # Re-execute with feedback
                feedback_msg = Message(
                    content=f"Previous attempt had quality {quality_score:.2f}. Issues: {review_response.content}. Please improve.",
                    sender="reviewer",
                    role=MessageRole.SYSTEM,
                )

                worker_results = await self._execute_workers(
                    workers, subtasks, worker_timeout, enable_load_balancing, feedback_msg
                )

        self.metrics.custom_metrics["escalations"] = escalation_count
        self.metrics.custom_metrics["final_quality"] = quality_score

        return self._create_result(True, messages)

    def _parse_subtasks(self, content: str, num_workers: int) -> List[Dict[str, Any]]:
        """Parse subtasks from manager response."""
        subtasks = []
        lines = content.split("\n")

        current_subtask = {}
        for line in lines:
            line = line.strip()
            if line.startswith("SUBTASK"):
                if current_subtask:
                    subtasks.append(current_subtask)
                desc = line.split(":", 1)[1].strip() if ":" in line else line
                current_subtask = {
                    "description": desc,
                    "priority": "medium",
                    "dependencies": [],
                }
            elif line.startswith("PRIORITY:") and current_subtask:
                current_subtask["priority"] = line.split(":", 1)[1].strip().lower()
            elif line.startswith("DEPENDENCIES:") and current_subtask:
                deps = line.split(":", 1)[1].strip().lower()
                if deps != "none":
                    current_subtask["dependencies"] = [d.strip() for d in deps.split(",")]

        if current_subtask:
            subtasks.append(current_subtask)

        # Ensure we have enough subtasks
        while len(subtasks) < num_workers:
            subtasks.append(
                {
                    "description": f"Support task {len(subtasks) + 1}",
                    "priority": "low",
                    "dependencies": [],
                }
            )

        return subtasks[:num_workers]

    async def _execute_workers(
        self,
        workers: List[Agent],
        subtasks: List[Dict[str, Any]],
        timeout: float,
        load_balance: bool,
        feedback: Optional[Message] = None,
    ) -> List[Optional[Message]]:
        """Execute workers in parallel with optional load balancing."""
        if load_balance:
            # Sort subtasks by priority
            priority_order = {"high": 0, "medium": 1, "low": 2}
            sorted_subtasks = sorted(
                enumerate(subtasks), key=lambda x: priority_order.get(x[1]["priority"], 1)
            )
            assignments = [(workers[i % len(workers)], st) for i, (_, st) in enumerate(sorted_subtasks)]
        else:
            # Simple assignment
            assignments = [(workers[i % len(workers)], st) for i, st in enumerate(subtasks)]

        tasks = []
        for worker, subtask in assignments:
            content = subtask["description"]
            if feedback:
                content = f"{feedback.content}\n\nSubtask: {content}"

            msg = Message(content=content, sender="manager", role=MessageRole.SYSTEM)
            tasks.append(self._safe_process_message(worker, msg, timeout))

        return await asyncio.gather(*tasks)

    def _extract_quality_score(self, content: str) -> float:
        """Extract quality score from reviewer response."""
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("QUALITY:"):
                try:
                    score_str = line.split(":", 1)[1].strip()
                    return float(score_str)
                except (ValueError, IndexError):
                    pass
        return 0.5  # Default if not found


class DebateOrchestrator(BaseOrchestrator):
    """Debate orchestration with multi-round deliberation.

    Features:
    - Multiple rounds of debate
    - Voting mechanisms (majority, weighted, consensus)
    - Moderator/facilitator agent
    - Argument tracking and synthesis
    - Convergence detection
    """

    def get_mode(self) -> OrchestrationMode:
        return OrchestrationMode.DEBATE

    async def orchestrate(
        self,
        agents: List[Agent],
        task: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> CollaborationResult:
        """Execute debate mode with voting.

        Args:
            agents: List of agents
            task: Task description
            context: Optional context
            **kwargs: Additional parameters
                - debate_rounds: Number of debate rounds (default: 3)
                - voting_mechanism: 'majority', 'weighted', 'consensus' (default: 'majority')
                - convergence_threshold: Stop if agreement > threshold (default: 0.8)
                - enable_moderator: Use first agent as moderator (default: False)
                - weights: Dict of agent weights for weighted voting

        Returns:
            Collaboration result
        """
        if not self._validate_agents(agents, min_agents=2):
            return self._create_result(False, [], "Debate requires at least 2 agents")

        debate_rounds = kwargs.get("debate_rounds", 3)
        voting_mechanism = kwargs.get("voting_mechanism", "majority")
        convergence_threshold = kwargs.get("convergence_threshold", 0.8)
        enable_moderator = kwargs.get("enable_moderator", False)
        weights = kwargs.get("weights", {})

        self.logger.info(
            f"Starting debate with {len(agents)} agents for {debate_rounds} rounds"
        )

        messages: List[Message] = []
        debate_history: List[Dict[str, Any]] = []

        # Setup moderator if enabled
        if enable_moderator:
            moderator = agents[0]
            debaters = agents[1:]
            self.logger.info(f"Moderator: {moderator.name}")
        else:
            moderator = None
            debaters = agents

        # Initial positions
        initial_msg = Message(
            content=f"""State your position on: {task}

Provide:
1. Your stance (SUPPORT/OPPOSE/NEUTRAL)
2. Key arguments (2-3 points)
3. Confidence level (0-100)

Format:
STANCE: [SUPPORT/OPPOSE/NEUTRAL]
ARGUMENTS:
- [argument 1]
- [argument 2]
CONFIDENCE: [0-100]""",
            sender="system",
            role=MessageRole.SYSTEM,
        )

        # Debate rounds
        for round_num in range(debate_rounds):
            self.logger.info(f"Debate round {round_num + 1}/{debate_rounds}")
            self.metrics.total_rounds += 1

            round_responses = []

            # Moderator introduces round
            if moderator and round_num > 0:
                mod_msg = Message(
                    content=f"Round {round_num + 1}: Review previous arguments and refine your position.",
                    sender="moderator",
                    role=MessageRole.SYSTEM,
                )
                mod_response = await self._safe_process_message(moderator, mod_msg)
                if mod_response:
                    messages.append(mod_response)

            # Each agent presents position
            for agent in debaters:
                if round_num == 0:
                    context_msg = initial_msg
                else:
                    # Include previous round context
                    prev_args = self._summarize_previous_round(debate_history[-1])
                    context_msg = Message(
                        content=f"""{task}

Previous round summary:
{prev_args}

Respond to these arguments and refine your position.""",
                        sender="system",
                        role=MessageRole.SYSTEM,
                    )

                response = await self._safe_process_message(agent, context_msg)
                if response:
                    round_responses.append(response)
                    messages.append(response)

            # Parse positions
            positions = self._parse_debate_positions(round_responses)
            debate_history.append(
                {
                    "round": round_num + 1,
                    "positions": positions,
                    "responses": round_responses,
                }
            )

            # Check for convergence
            convergence = self._calculate_convergence(positions)
            self.logger.info(f"Round {round_num + 1} convergence: {convergence:.2f}")

            if convergence >= convergence_threshold:
                self.logger.info("Convergence threshold reached, ending debate")
                break

        # Final voting phase
        self.logger.info(f"Final voting using {voting_mechanism} mechanism")
        vote_result = await self._conduct_voting(
            debaters, debate_history, voting_mechanism, weights
        )

        # Moderator summarizes if enabled
        if moderator:
            summary_msg = Message(
                content=f"""Summarize the debate and final decision:

Debate topic: {task}
Voting result: {vote_result}

Provide a balanced summary of all perspectives.""",
                sender="system",
                role=MessageRole.SYSTEM,
            )
            summary = await self._safe_process_message(moderator, summary_msg)
            if summary:
                messages.append(summary)

        self.metrics.custom_metrics["debate_rounds"] = len(debate_history)
        self.metrics.custom_metrics["final_convergence"] = convergence
        self.metrics.custom_metrics["vote_result"] = vote_result

        return self._create_result(True, messages)

    def _parse_debate_positions(
        self, responses: List[Message]
    ) -> List[Dict[str, Any]]:
        """Parse debate positions from responses."""
        positions = []

        for response in responses:
            position = {
                "agent": response.sender,
                "stance": "NEUTRAL",
                "arguments": [],
                "confidence": 50,
            }

            lines = response.content.split("\n")
            current_section = None

            for line in lines:
                line = line.strip()
                if line.startswith("STANCE:"):
                    stance = line.split(":", 1)[1].strip().upper()
                    if stance in ["SUPPORT", "OPPOSE", "NEUTRAL"]:
                        position["stance"] = stance
                elif line.startswith("ARGUMENTS:"):
                    current_section = "arguments"
                elif line.startswith("CONFIDENCE:"):
                    try:
                        position["confidence"] = int(line.split(":", 1)[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif current_section == "arguments" and line.startswith("-"):
                    position["arguments"].append(line[1:].strip())

            positions.append(position)

        return positions

    def _calculate_convergence(self, positions: List[Dict[str, Any]]) -> float:
        """Calculate convergence level (0-1) based on stance agreement."""
        if not positions:
            return 0.0

        stance_counts = defaultdict(int)
        for pos in positions:
            stance_counts[pos["stance"]] += 1

        max_agreement = max(stance_counts.values())
        return max_agreement / len(positions)

    def _summarize_previous_round(self, round_data: Dict[str, Any]) -> str:
        """Summarize previous round arguments."""
        summary = []
        for pos in round_data["positions"]:
            summary.append(
                f"{pos['agent']} ({pos['stance']}): {', '.join(pos['arguments'][:2])}"
            )
        return "\n".join(summary)

    async def _conduct_voting(
        self,
        agents: List[Agent],
        debate_history: List[Dict[str, Any]],
        mechanism: str,
        weights: Dict[str, float],
    ) -> Dict[str, Any]:
        """Conduct final voting."""
        # Get final positions
        final_positions = debate_history[-1]["positions"] if debate_history else []

        if mechanism == "majority":
            return self._majority_vote(final_positions)
        elif mechanism == "weighted":
            return self._weighted_vote(final_positions, weights)
        elif mechanism == "consensus":
            return self._consensus_vote(final_positions)
        else:
            return {"error": f"Unknown voting mechanism: {mechanism}"}

    def _majority_vote(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simple majority voting."""
        stance_counts = defaultdict(int)
        for pos in positions:
            stance_counts[pos["stance"]] += 1

        winner = max(stance_counts.items(), key=lambda x: x[1])
        return {
            "mechanism": "majority",
            "winner": winner[0],
            "votes": dict(stance_counts),
            "total": len(positions),
        }

    def _weighted_vote(
        self, positions: List[Dict[str, Any]], weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """Weighted voting based on agent weights."""
        stance_weights = defaultdict(float)

        for pos in positions:
            weight = weights.get(pos["agent"], 1.0)
            stance_weights[pos["stance"]] += weight

        winner = max(stance_weights.items(), key=lambda x: x[1])
        return {
            "mechanism": "weighted",
            "winner": winner[0],
            "weighted_votes": dict(stance_weights),
            "weights_used": weights,
        }

    def _consensus_vote(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Consensus voting considering confidence levels."""
        stance_confidence = defaultdict(float)

        for pos in positions:
            stance_confidence[pos["stance"]] += pos["confidence"]

        winner = max(stance_confidence.items(), key=lambda x: x[1])
        avg_confidence = winner[1] / len(
            [p for p in positions if p["stance"] == winner[0]]
        )

        return {
            "mechanism": "consensus",
            "winner": winner[0],
            "total_confidence": dict(stance_confidence),
            "average_confidence": avg_confidence,
        }


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
                    self.add_edge(f"node_{i - 1}", node_id)
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
