"""
OpenTelemetry and observability integration for AgentMind.

This module provides comprehensive observability with:
- OpenTelemetry tracing
- Langfuse LLM observability
- Custom metrics and spans
"""

import logging
import time
from typing import Any, Dict, Optional
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

logger = logging.getLogger(__name__)


class ObservabilityManager:
    """Manages observability for AgentMind."""

    def __init__(
        self,
        service_name: str = "agentmind",
        enable_console: bool = False,
        otlp_endpoint: Optional[str] = None,
        langfuse_enabled: bool = False,
        langfuse_public_key: Optional[str] = None,
        langfuse_secret_key: Optional[str] = None,
    ):
        """Initialize observability manager.

        Args:
            service_name: Name of the service
            enable_console: Enable console exporter for debugging
            otlp_endpoint: OTLP endpoint for trace export
            langfuse_enabled: Enable Langfuse integration
            langfuse_public_key: Langfuse public key
            langfuse_secret_key: Langfuse secret key
        """
        self.service_name = service_name
        self.tracer_provider = None
        self.tracer = None
        self.langfuse_client = None

        # Initialize OpenTelemetry
        self._setup_opentelemetry(enable_console, otlp_endpoint)

        # Initialize Langfuse if enabled
        if langfuse_enabled:
            self._setup_langfuse(langfuse_public_key, langfuse_secret_key)

    def _setup_opentelemetry(self, enable_console: bool, otlp_endpoint: Optional[str]):
        """Set up OpenTelemetry tracing."""
        try:
            # Create resource
            resource = Resource.create(
                {"service.name": self.service_name, "service.version": "0.3.0"}
            )

            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=resource)

            # Add console exporter if enabled
            if enable_console:
                console_exporter = ConsoleSpanExporter()
                console_processor = BatchSpanProcessor(console_exporter)
                self.tracer_provider.add_span_processor(console_processor)

            # Add OTLP exporter if endpoint provided
            if otlp_endpoint:
                otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                otlp_processor = BatchSpanProcessor(otlp_exporter)
                self.tracer_provider.add_span_processor(otlp_processor)

            # Set global tracer provider
            trace.set_tracer_provider(self.tracer_provider)

            # Get tracer
            self.tracer = trace.get_tracer(__name__)

            logger.info("OpenTelemetry initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")

    def _setup_langfuse(self, public_key: Optional[str], secret_key: Optional[str]):
        """Set up Langfuse integration."""
        try:
            from langfuse import Langfuse

            if not public_key or not secret_key:
                logger.warning("Langfuse keys not provided, skipping initialization")
                return

            self.langfuse_client = Langfuse(public_key=public_key, secret_key=secret_key)

            logger.info("Langfuse initialized successfully")

        except ImportError:
            logger.warning("Langfuse not installed, skipping initialization")
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse: {e}")

    @contextmanager
    def trace_operation(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None):
        """Context manager for tracing operations.

        Args:
            operation_name: Name of the operation
            attributes: Additional attributes to add to the span

        Yields:
            Span object
        """
        if not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(operation_name) as span:
            # Add attributes
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))

            # Add timestamp
            span.set_attribute("timestamp", time.time())

            try:
                yield span
            except Exception as e:
                # Record exception
                span.record_exception(e)
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                raise

    def trace_llm_call(
        self,
        model: str,
        prompt: str,
        response: str,
        token_usage: Dict[str, int],
        duration_ms: float,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Trace an LLM call.

        Args:
            model: Model name
            prompt: Input prompt
            response: Model response
            token_usage: Token usage statistics
            duration_ms: Duration in milliseconds
            metadata: Additional metadata
        """
        # OpenTelemetry span
        if self.tracer:
            with self.tracer.start_as_current_span("llm_call") as span:
                span.set_attribute("llm.model", model)
                span.set_attribute("llm.prompt_length", len(prompt))
                span.set_attribute("llm.response_length", len(response))
                span.set_attribute("llm.input_tokens", token_usage.get("input_tokens", 0))
                span.set_attribute("llm.output_tokens", token_usage.get("output_tokens", 0))
                span.set_attribute("llm.duration_ms", duration_ms)

                if metadata:
                    for key, value in metadata.items():
                        span.set_attribute(f"llm.{key}", str(value))

        # Langfuse trace
        if self.langfuse_client:
            try:
                trace = self.langfuse_client.trace(name="llm_call", metadata=metadata or {})

                trace.generation(
                    name=model,
                    model=model,
                    input=prompt,
                    output=response,
                    usage={
                        "input": token_usage.get("input_tokens", 0),
                        "output": token_usage.get("output_tokens", 0),
                        "total": token_usage.get("total_tokens", 0),
                    },
                    metadata={"duration_ms": duration_ms, **(metadata or {})},
                )

            except Exception as e:
                logger.error(f"Failed to trace LLM call in Langfuse: {e}")

    def trace_collaboration(
        self,
        session_id: str,
        task: str,
        agents: list,
        result: str,
        rounds: int,
        duration_ms: float,
        token_usage: Dict[str, int],
        cost: float,
    ):
        """Trace a collaboration session.

        Args:
            session_id: Session identifier
            task: Task description
            agents: List of agent names
            result: Collaboration result
            rounds: Number of rounds
            duration_ms: Duration in milliseconds
            token_usage: Token usage statistics
            cost: Estimated cost
        """
        if self.tracer:
            with self.tracer.start_as_current_span("collaboration") as span:
                span.set_attribute("collaboration.session_id", session_id)
                span.set_attribute("collaboration.task_length", len(task))
                span.set_attribute("collaboration.num_agents", len(agents))
                span.set_attribute("collaboration.rounds", rounds)
                span.set_attribute("collaboration.duration_ms", duration_ms)
                span.set_attribute("collaboration.total_tokens", token_usage.get("total_tokens", 0))
                span.set_attribute("collaboration.cost_usd", cost)

        if self.langfuse_client:
            try:
                trace = self.langfuse_client.trace(
                    name="collaboration",
                    session_id=session_id,
                    metadata={
                        "task": task[:100],
                        "agents": agents,
                        "rounds": rounds,
                        "duration_ms": duration_ms,
                        "cost_usd": cost,
                    },
                )

                trace.span(
                    name="collaboration_complete",
                    input=task,
                    output=result,
                    metadata={"token_usage": token_usage, "cost": cost},
                )

            except Exception as e:
                logger.error(f"Failed to trace collaboration in Langfuse: {e}")

    def flush(self):
        """Flush all pending traces."""
        if self.tracer_provider:
            self.tracer_provider.force_flush()

        if self.langfuse_client:
            try:
                self.langfuse_client.flush()
            except Exception as e:
                logger.error(f"Failed to flush Langfuse: {e}")


# Global observability manager instance
_observability_manager: Optional[ObservabilityManager] = None


def get_observability_manager() -> Optional[ObservabilityManager]:
    """Get the global observability manager instance."""
    return _observability_manager


def initialize_observability(
    service_name: str = "agentmind",
    enable_console: bool = False,
    otlp_endpoint: Optional[str] = None,
    langfuse_enabled: bool = False,
    langfuse_public_key: Optional[str] = None,
    langfuse_secret_key: Optional[str] = None,
) -> ObservabilityManager:
    """Initialize global observability manager.

    Args:
        service_name: Name of the service
        enable_console: Enable console exporter for debugging
        otlp_endpoint: OTLP endpoint for trace export
        langfuse_enabled: Enable Langfuse integration
        langfuse_public_key: Langfuse public key
        langfuse_secret_key: Langfuse secret key

    Returns:
        ObservabilityManager instance
    """
    global _observability_manager

    _observability_manager = ObservabilityManager(
        service_name=service_name,
        enable_console=enable_console,
        otlp_endpoint=otlp_endpoint,
        langfuse_enabled=langfuse_enabled,
        langfuse_public_key=langfuse_public_key,
        langfuse_secret_key=langfuse_secret_key,
    )

    return _observability_manager
