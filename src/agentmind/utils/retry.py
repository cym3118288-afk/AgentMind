"""Retry and error recovery utilities for AgentMind.

This module provides robust retry mechanisms with exponential backoff,
fallback strategies, and error handling for LLM calls and agent operations.
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig(BaseModel):
    """Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay in seconds between retries
        exponential_base: Base for exponential backoff calculation
        jitter: Add random jitter to delays (0.0-1.0)
        retry_on_exceptions: Exception types to retry on
    """

    max_attempts: int = Field(default=3, ge=1, description="Maximum retry attempts")
    initial_delay: float = Field(default=1.0, ge=0.1, description="Initial delay in seconds")
    max_delay: float = Field(default=60.0, ge=1.0, description="Maximum delay in seconds")
    exponential_base: float = Field(default=2.0, ge=1.0, description="Exponential backoff base")
    jitter: float = Field(default=0.1, ge=0.0, le=1.0, description="Random jitter factor")
    retry_on_exceptions: List[Type[Exception]] = Field(
        default_factory=lambda: [Exception], description="Exception types to retry on"
    )


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, attempts: int, last_error: Exception):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Retry exhausted after {attempts} attempts. Last error: {last_error}")


def calculate_delay(attempt: int, config: RetryConfig, jitter: bool = True) -> float:
    """Calculate delay for a retry attempt with exponential backoff.

    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
        jitter: Whether to add random jitter

    Returns:
        Delay in seconds
    """
    import random

    # Exponential backoff: initial_delay * (base ^ attempt)
    delay = config.initial_delay * (config.exponential_base**attempt)

    # Cap at max_delay
    delay = min(delay, config.max_delay)

    # Add jitter if enabled
    if jitter and config.jitter > 0:
        jitter_amount = delay * config.jitter * random.random()
        delay += jitter_amount

    return delay


async def retry_async(
    func: Callable[..., T],
    *args: Any,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    **kwargs: Any,
) -> T:
    """Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Positional arguments for func
        config: Retry configuration (uses defaults if None)
        on_retry: Optional callback called on each retry (attempt, error)
        **kwargs: Keyword arguments for func

    Returns:
        Result from successful function call

    Raises:
        RetryExhaustedError: If all retry attempts fail

    Example:
        >>> async def flaky_api_call():
        ...     # May fail occasionally
        ...     return await some_api()
        >>> result = await retry_async(flaky_api_call, config=RetryConfig(max_attempts=5))
    """
    if config is None:
        config = RetryConfig()

    last_error = None

    for attempt in range(config.max_attempts):
        try:
            result = await func(*args, **kwargs)

            # Success - log if this was a retry
            if attempt > 0:
                logger.info(f"Retry succeeded on attempt {attempt + 1}/{config.max_attempts}")

            return result

        except tuple(config.retry_on_exceptions) as e:
            last_error = e

            # Log the error
            logger.warning(
                f"Attempt {attempt + 1}/{config.max_attempts} failed: {type(e).__name__}: {e}"
            )

            # Call retry callback if provided
            if on_retry:
                try:
                    on_retry(attempt, e)
                except Exception as callback_error:
                    logger.error(f"Retry callback failed: {callback_error}")

            # If this was the last attempt, raise
            if attempt == config.max_attempts - 1:
                raise RetryExhaustedError(config.max_attempts, last_error)

            # Calculate delay and wait
            delay = calculate_delay(attempt, config)
            logger.info(f"Retrying in {delay:.2f} seconds...")
            await asyncio.sleep(delay)

    # Should never reach here, but just in case
    raise RetryExhaustedError(config.max_attempts, last_error or Exception("Unknown error"))


def with_retry(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
):
    """Decorator to add retry logic to async functions.

    Args:
        config: Retry configuration
        on_retry: Optional callback on each retry

    Returns:
        Decorated function with retry logic

    Example:
        >>> @with_retry(config=RetryConfig(max_attempts=3))
        ... async def fetch_data():
        ...     return await api.get_data()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_async(func, *args, config=config, on_retry=on_retry, **kwargs)

        return wrapper

    return decorator


def retry_with_backoff(config: Optional[RetryConfig] = None):
    """Decorator to add retry logic to sync functions.

    Args:
        config: Retry configuration

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            if config is None:
                retry_config = RetryConfig()
            else:
                retry_config = config

            last_error = None
            for attempt in range(retry_config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except tuple(retry_config.retry_on_exceptions) as e:
                    last_error = e
                    if attempt == retry_config.max_attempts - 1:
                        raise RetryExhaustedError(retry_config.max_attempts, last_error)
                    import time

                    delay = calculate_delay(attempt, retry_config)
                    time.sleep(delay)
            raise RetryExhaustedError(retry_config.max_attempts, last_error or Exception("Unknown"))

        return wrapper

    return decorator


def async_retry_with_backoff(config: Optional[RetryConfig] = None):
    """Decorator to add retry logic to async functions (alias for with_retry).

    Args:
        config: Retry configuration

    Returns:
        Decorated function with retry logic
    """
    return with_retry(config=config)


class FallbackChain:
    """Chain of fallback strategies for robust error handling.

    Tries multiple strategies in order until one succeeds.

    Example:
        >>> chain = FallbackChain()
        >>> chain.add_strategy(primary_llm_call)
        >>> chain.add_strategy(backup_llm_call)
        >>> chain.add_strategy(lambda: "Default response")
        >>> result = await chain.execute()
    """

    def __init__(self):
        """Initialize an empty fallback chain."""
        self.strategies: List[Callable] = []

    def add_strategy(self, func: Callable[..., T]) -> "FallbackChain":
        """Add a fallback strategy to the chain.

        Args:
            func: Async or sync function to try

        Returns:
            Self for method chaining
        """
        self.strategies.append(func)
        return self

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute strategies in order until one succeeds.

        Args:
            *args: Arguments to pass to each strategy
            **kwargs: Keyword arguments to pass to each strategy

        Returns:
            Result from first successful strategy

        Raises:
            Exception: If all strategies fail
        """
        if not self.strategies:
            raise ValueError("No fallback strategies configured")

        errors = []

        for i, strategy in enumerate(self.strategies):
            try:
                logger.info(f"Trying fallback strategy {i + 1}/{len(self.strategies)}")

                # Handle both async and sync functions
                if asyncio.iscoroutinefunction(strategy):
                    result = await strategy(*args, **kwargs)
                else:
                    result = strategy(*args, **kwargs)

                # Success
                if i > 0:
                    logger.info(f"Fallback strategy {i + 1} succeeded")

                return result

            except Exception as e:
                errors.append((i, type(e).__name__, str(e)))
                logger.warning(f"Fallback strategy {i + 1} failed: {e}")

                # If this was the last strategy, raise
                if i == len(self.strategies) - 1:
                    error_summary = "; ".join(
                        f"Strategy {idx + 1}: {name}" for idx, name, _ in errors
                    )
                    raise Exception(
                        f"All {len(self.strategies)} fallback strategies failed. "
                        f"Errors: {error_summary}"
                    ) from e

        # Should never reach here
        raise Exception("Fallback chain execution failed unexpectedly")


# Re-export RateLimiter for backward compatibility
try:
    from ..security.rate_limiter import RateLimiter as _RateLimiter

    RateLimiter = _RateLimiter
except ImportError:
    pass


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascading failures.

    Tracks failures and temporarily stops calling a failing service
    to allow it time to recover.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service has recovered

    Example:
        >>> breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        >>> async def call_api():
        ...     async with breaker:
        ...         return await api.call()
    """

    def __init__(
        self, failure_threshold: int = 5, timeout: float = 60.0, half_open_attempts: int = 1
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery
            half_open_attempts: Number of test attempts in half-open state
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_attempts = half_open_attempts

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.half_open_count = 0

    async def __aenter__(self):
        """Enter circuit breaker context."""
        import time

        # Check if we should transition from OPEN to HALF_OPEN
        if self.state == "OPEN":
            if self.last_failure_time and (time.time() - self.last_failure_time) >= self.timeout:
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                self.state = "HALF_OPEN"
                self.half_open_count = 0
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit circuit breaker context."""
        import time

        if exc_type is None:
            # Success
            if self.state == "HALF_OPEN":
                self.half_open_count += 1
                if self.half_open_count >= self.half_open_attempts:
                    logger.info("Circuit breaker transitioning to CLOSED")
                    self.state = "CLOSED"
                    self.failure_count = 0
            elif self.state == "CLOSED":
                # Reset failure count on success
                self.failure_count = 0
        else:
            # Failure
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == "HALF_OPEN":
                logger.warning("Circuit breaker transitioning back to OPEN")
                self.state = "OPEN"
            elif self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
                logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")
                self.state = "OPEN"

        return False  # Don't suppress exceptions
