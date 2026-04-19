"""Observability and tracing utilities for AgentMind.

This module provides comprehensive tracing, logging, and cost tracking
for multi-agent collaborations.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TokenUsage(BaseModel):
    """Token usage information for an LLM call.

    Attributes:
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total tokens used
    """

    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class CostEstimate(BaseModel):
    """Cost estimate for LLM usage.

    Attributes:
        prompt_cost: Cost for prompt tokens
        completion_cost: Cost for completion tokens
        total_cost: Total estimated cost in USD
        model: Model used for pricing
    """

    prompt_cost: float = Field(default=0.0, ge=0.0)
    completion_cost: float = Field(default=0.0, ge=0.0)
    total_cost: float = Field(default=0.0, ge=0.0)
    model: str = Field(default="unknown")


class TraceEvent(BaseModel):
    """A single trace event in the collaboration.

    Attributes:
        timestamp: ISO timestamp of the event
        event_type: Type of event (agent_message, tool_call, llm_call, etc.)
        agent_name: Name of the agent involved
        data: Event-specific data
        duration_ms: Duration in milliseconds (if applicable)
        metadata: Additional metadata
    """

    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    event_type: str = Field(..., description="Event type")
    agent_name: Optional[str] = Field(None, description="Agent name")
    data: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[float] = Field(None, ge=0.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CollaborationTrace(BaseModel):
    """Complete trace of a multi-agent collaboration.

    Attributes:
        session_id: Unique identifier for this collaboration session
        start_time: ISO timestamp when collaboration started
        end_time: ISO timestamp when collaboration ended
        events: List of trace events
        total_duration_ms: Total duration in milliseconds
        token_usage: Aggregated token usage
        cost_estimate: Estimated cost
        metadata: Session metadata
    """

    session_id: str = Field(..., description="Unique session identifier")
    start_time: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time: Optional[str] = None
    events: List[TraceEvent] = Field(default_factory=list)
    total_duration_ms: Optional[float] = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    cost_estimate: CostEstimate = Field(default_factory=CostEstimate)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Tracer:
    """Tracer for recording and analyzing multi-agent collaborations.

    Example:
        >>> tracer = Tracer(session_id="collab-001")
        >>> tracer.start()
        >>> tracer.log_event("agent_message", agent_name="analyst", data={"content": "..."})
        >>> tracer.end()
        >>> tracer.save_jsonl("traces/collab-001.jsonl")
    """

    def __init__(
        self,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        auto_save: bool = False,
        save_path: Optional[Path] = None
    ):
        """Initialize tracer.

        Args:
            session_id: Unique identifier for this session
            metadata: Optional session metadata
            auto_save: Whether to auto-save after each event
            save_path: Path to save traces (if auto_save is True)
        """
        self.trace = CollaborationTrace(
            session_id=session_id,
            metadata=metadata or {}
        )
        self.auto_save = auto_save
        self.save_path = save_path
        self._start_time: Optional[float] = None

    def start(self) -> None:
        """Start the trace timer."""
        self._start_time = time.time()
        self.trace.start_time = datetime.utcnow().isoformat()

    def end(self) -> None:
        """End the trace and calculate total duration."""
        if self._start_time:
            duration = (time.time() - self._start_time) * 1000  # Convert to ms
            self.trace.total_duration_ms = duration
        self.trace.end_time = datetime.utcnow().isoformat()

        if self.auto_save and self.save_path:
            self.save_jsonl(self.save_path)

    def log_event(
        self,
        event_type: str,
        agent_name: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a trace event.

        Args:
            event_type: Type of event
            agent_name: Name of agent involved
            data: Event data
            duration_ms: Duration in milliseconds
            metadata: Additional metadata
        """
        event = TraceEvent(
            event_type=event_type,
            agent_name=agent_name,
            data=data or {},
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        self.trace.events.append(event)

        if self.auto_save and self.save_path:
            self._append_event_to_file(event)

    def log_llm_call(
        self,
        agent_name: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_ms: float,
        cost: Optional[float] = None
    ) -> None:
        """Log an LLM call with token usage.

        Args:
            agent_name: Name of agent making the call
            model: Model used
            prompt_tokens: Prompt tokens used
            completion_tokens: Completion tokens used
            duration_ms: Call duration in milliseconds
            cost: Estimated cost in USD
        """
        # Update aggregated token usage
        self.trace.token_usage.prompt_tokens += prompt_tokens
        self.trace.token_usage.completion_tokens += completion_tokens
        self.trace.token_usage.total_tokens += (prompt_tokens + completion_tokens)

        # Update cost estimate
        if cost:
            self.trace.cost_estimate.total_cost += cost

        # Log event
        self.log_event(
            event_type="llm_call",
            agent_name=agent_name,
            data={
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost": cost
            },
            duration_ms=duration_ms
        )

    def log_tool_call(
        self,
        agent_name: str,
        tool_name: str,
        params: Dict[str, Any],
        result: Any,
        duration_ms: float,
        success: bool = True
    ) -> None:
        """Log a tool execution.

        Args:
            agent_name: Name of agent using the tool
            tool_name: Name of tool
            params: Tool parameters
            result: Tool result
            duration_ms: Execution duration
            success: Whether tool call succeeded
        """
        self.log_event(
            event_type="tool_call",
            agent_name=agent_name,
            data={
                "tool_name": tool_name,
                "params": params,
                "result": result,
                "success": success
            },
            duration_ms=duration_ms
        )

    def save_jsonl(self, path: Union[str, Path]) -> None:
        """Save trace to JSONL file (one event per line).

        Args:
            path: Path to save file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            # Write metadata header
            header = {
                "session_id": self.trace.session_id,
                "start_time": self.trace.start_time,
                "end_time": self.trace.end_time,
                "total_duration_ms": self.trace.total_duration_ms,
                "token_usage": self.trace.token_usage.model_dump(),
                "cost_estimate": self.trace.cost_estimate.model_dump(),
                "metadata": self.trace.metadata
            }
            f.write(json.dumps({"type": "header", "data": header}) + "\n")

            # Write events
            for event in self.trace.events:
                f.write(json.dumps({"type": "event", "data": event.model_dump()}) + "\n")

        logger.info(f"Trace saved to {path}")

    def _append_event_to_file(self, event: TraceEvent) -> None:
        """Append a single event to the trace file.

        Args:
            event: Event to append
        """
        if not self.save_path:
            return

        path = Path(self.save_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"type": "event", "data": event.model_dump()}) + "\n")

    def save_json(self, path: Union[str, Path]) -> None:
        """Save complete trace to JSON file.

        Args:
            path: Path to save file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.trace.model_dump(), f, indent=2)

        logger.info(f"Trace saved to {path}")

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the trace.

        Returns:
            Dictionary with summary statistics
        """
        agent_events = {}
        event_types = {}

        for event in self.trace.events:
            # Count by agent
            if event.agent_name:
                agent_events[event.agent_name] = agent_events.get(event.agent_name, 0) + 1

            # Count by event type
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1

        return {
            "session_id": self.trace.session_id,
            "total_events": len(self.trace.events),
            "total_duration_ms": self.trace.total_duration_ms,
            "token_usage": self.trace.token_usage.model_dump(),
            "cost_estimate": self.trace.cost_estimate.model_dump(),
            "events_by_agent": agent_events,
            "events_by_type": event_types,
            "start_time": self.trace.start_time,
            "end_time": self.trace.end_time
        }

    def generate_mermaid_diagram(self) -> str:
        """Generate a Mermaid sequence diagram of the collaboration.

        Returns:
            Mermaid diagram as string
        """
        lines = ["sequenceDiagram"]

        # Track participants
        participants = set()
        for event in self.trace.events:
            if event.agent_name:
                participants.add(event.agent_name)

        # Add participants
        for participant in sorted(participants):
            lines.append(f"    participant {participant}")

        # Add events
        for i, event in enumerate(self.trace.events):
            if event.event_type == "agent_message":
                sender = event.agent_name or "System"
                receiver = event.data.get("receiver", "All")
                content = event.data.get("content", "")[:50]  # Truncate
                lines.append(f"    {sender}->>+{receiver}: {content}")

            elif event.event_type == "tool_call":
                agent = event.agent_name or "Agent"
                tool = event.data.get("tool_name", "Tool")
                lines.append(f"    {agent}->>+{tool}: Execute")
                lines.append(f"    {tool}-->>-{agent}: Result")

            elif event.event_type == "llm_call":
                agent = event.agent_name or "Agent"
                model = event.data.get("model", "LLM")
                lines.append(f"    {agent}->>+{model}: Generate")
                lines.append(f"    {model}-->>-{agent}: Response")

        return "\n".join(lines)


class CostTracker:
    """Track and estimate costs for LLM usage.

    Pricing data for common models (as of 2026).
    """

    # Pricing per 1M tokens (USD)
    PRICING = {
        # OpenAI
        "gpt-4": {"prompt": 30.0, "completion": 60.0},
        "gpt-4-turbo": {"prompt": 10.0, "completion": 30.0},
        "gpt-3.5-turbo": {"prompt": 0.5, "completion": 1.5},
        # Anthropic
        "claude-3-opus": {"prompt": 15.0, "completion": 75.0},
        "claude-3-sonnet": {"prompt": 3.0, "completion": 15.0},
        "claude-3-haiku": {"prompt": 0.25, "completion": 1.25},
        # Google
        "gemini-pro": {"prompt": 0.5, "completion": 1.5},
        "gemini-ultra": {"prompt": 10.0, "completion": 30.0},
        # Local models (free)
        "ollama": {"prompt": 0.0, "completion": 0.0},
    }

    @classmethod
    def estimate_cost(
        cls,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> CostEstimate:
        """Estimate cost for an LLM call.

        Args:
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Cost estimate
        """
        # Find pricing (try exact match, then prefix match)
        pricing = None
        for key, value in cls.PRICING.items():
            if model.startswith(key):
                pricing = value
                break

        if not pricing:
            # Unknown model, use default pricing
            pricing = {"prompt": 1.0, "completion": 2.0}

        # Calculate costs (pricing is per 1M tokens)
        prompt_cost = (prompt_tokens / 1_000_000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * pricing["completion"]

        return CostEstimate(
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            total_cost=prompt_cost + completion_cost,
            model=model
        )

    @classmethod
    def add_pricing(cls, model: str, prompt_price: float, completion_price: float) -> None:
        """Add custom pricing for a model.

        Args:
            model: Model name
            prompt_price: Price per 1M prompt tokens (USD)
            completion_price: Price per 1M completion tokens (USD)
        """
        cls.PRICING[model] = {"prompt": prompt_price, "completion": completion_price}
