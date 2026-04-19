"""Utility functions and helpers for AgentMind.

This module provides various utility functions for async operations,
prompt templates, tracing, and other common tasks.
"""

import asyncio
from typing import Any, Coroutine, List, TypeVar

from .exceptions import (
    AgentConfigError,
    AgentMindError,
    CollaborationError,
    LLMProviderError,
    MemoryError,
    ToolExecutionError,
    ValidationError,
    validate_agent_name,
    validate_max_rounds,
    validate_model_name,
)
from .observability import CostTracker, Tracer
from .retry import RetryConfig, retry_with_backoff

T = TypeVar("T")


async def gather_with_timeout(
    *coroutines: Coroutine[Any, Any, T], timeout: float = 30.0
) -> List[T]:
    """Gather coroutines with a timeout.

    Args:
        *coroutines: Coroutines to execute
        timeout: Timeout in seconds

    Returns:
        List of results

    Raises:
        asyncio.TimeoutError: If timeout is exceeded
    """
    return await asyncio.wait_for(asyncio.gather(*coroutines), timeout=timeout)


def format_prompt(template: str, **kwargs: Any) -> str:
    """Format a prompt template with variables.

    Args:
        template: Prompt template string
        **kwargs: Variables to substitute

    Returns:
        Formatted prompt string

    Example:
        >>> prompt = format_prompt("Hello {name}!", name="World")
        >>> print(prompt)
        Hello World!
    """
    return template.format(**kwargs)


__all__ = [
    "gather_with_timeout",
    "format_prompt",
    # Retry
    "RetryConfig",
    "retry_with_backoff",
    # Observability
    "Tracer",
    "CostTracker",
    # Exceptions
    "AgentMindError",
    "AgentConfigError",
    "CollaborationError",
    "LLMProviderError",
    "ToolExecutionError",
    "MemoryError",
    "ValidationError",
    "validate_agent_name",
    "validate_max_rounds",
    "validate_model_name",
]
