"""Example plugin templates for AgentMind.

This module provides templates for creating custom plugins.
"""

from typing import Any, Dict, List, Optional
from agentmind.plugins.interfaces import (
    LLMProvider,
    MemoryBackend,
    ToolRegistry,
    Orchestrator,
    Observer,
    PluginMetadata,
    PluginInterface,
)
from agentmind.core.types import Message


class ExampleLLMProvider(LLMProvider, PluginInterface):
    """Example LLM provider plugin template."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize provider."""
        self.config = config or {}
        self.model = self.config.get("model", "example-model")

    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            name="example-llm-provider",
            version="0.1.0",
            description="Example LLM provider plugin",
            author="Your Name",
            plugin_type="llm_provider",
        )

    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the plugin."""
        if config:
            self.config.update(config)
        print(f"[ExampleLLM] Initialized with model: {self.model}")

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        print("[ExampleLLM] Shutting down")

    def health_check(self) -> bool:
        """Check if plugin is healthy."""
        return True

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate response."""
        # Implement your LLM logic here
        return {
            "content": "Example response",
            "model": self.model,
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "metadata": {},
        }

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ):
        """Generate streaming response."""
        # Implement streaming logic
        yield "Example "
        yield "streaming "
        yield "response"

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "name": self.model,
            "max_tokens": 4096,
            "supports_streaming": True,
        }


class ExampleMemoryBackend(MemoryBackend, PluginInterface):
    """Example memory backend plugin template."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize backend."""
        self.config = config or {}
        self.storage: Dict[str, Any] = {}

    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            name="example-memory-backend",
            version="0.1.0",
            description="Example memory backend plugin",
            author="Your Name",
            plugin_type="memory",
        )

    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the plugin."""
        if config:
            self.config.update(config)
        print("[ExampleMemory] Initialized")

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        self.storage.clear()
        print("[ExampleMemory] Shutting down")

    def health_check(self) -> bool:
        """Check if plugin is healthy."""
        return True

    async def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store value."""
        self.storage[key] = {"value": value, "metadata": metadata or {}}

    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve value."""
        entry = self.storage.get(key)
        return entry["value"] if entry else None

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search memory."""
        # Implement search logic
        return []

    async def delete(self, key: str) -> bool:
        """Delete value."""
        if key in self.storage:
            del self.storage[key]
            return True
        return False

    async def clear(self) -> None:
        """Clear all memory."""
        self.storage.clear()

    async def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """List keys."""
        return list(self.storage.keys())


class ExampleOrchestrator(Orchestrator, PluginInterface):
    """Example orchestrator plugin template."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize orchestrator."""
        self.config = config or {}

    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            name="example-orchestrator",
            version="0.1.0",
            description="Example orchestrator plugin",
            author="Your Name",
            plugin_type="orchestration",
        )

    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the plugin."""
        if config:
            self.config.update(config)
        print("[ExampleOrchestrator] Initialized")

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        print("[ExampleOrchestrator] Shutting down")

    def health_check(self) -> bool:
        """Check if plugin is healthy."""
        return True

    async def orchestrate(
        self,
        agents: List[Any],
        task: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Orchestrate agents."""
        # Implement orchestration logic
        return {
            "success": True,
            "result": "Example orchestration result",
        }

    def get_strategy_name(self) -> str:
        """Get strategy name."""
        return "example"

    def supports_parallel(self) -> bool:
        """Check if supports parallel execution."""
        return True


class ExampleObserver(Observer, PluginInterface):
    """Example observer plugin template."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize observer."""
        self.config = config or {}
        self.events: List[Dict[str, Any]] = []

    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            name="example-observer",
            version="0.1.0",
            description="Example observer plugin",
            author="Your Name",
            plugin_type="observer",
        )

    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the plugin."""
        if config:
            self.config.update(config)
        print("[ExampleObserver] Initialized")

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        print("[ExampleObserver] Shutting down")

    def health_check(self) -> bool:
        """Check if plugin is healthy."""
        return True

    async def on_agent_start(self, agent_name: str, task: str, context: Dict[str, Any]) -> None:
        """Called when agent starts."""
        self.events.append(
            {
                "type": "agent_start",
                "agent": agent_name,
                "task": task,
            }
        )

    async def on_agent_end(self, agent_name: str, result: Any, context: Dict[str, Any]) -> None:
        """Called when agent ends."""
        self.events.append(
            {
                "type": "agent_end",
                "agent": agent_name,
                "result": str(result),
            }
        )

    async def on_agent_error(
        self,
        agent_name: str,
        error: Exception,
        context: Dict[str, Any],
    ) -> None:
        """Called when agent errors."""
        self.events.append(
            {
                "type": "agent_error",
                "agent": agent_name,
                "error": str(error),
            }
        )

    async def on_message(self, message: Message, context: Dict[str, Any]) -> None:
        """Called when message is sent."""
        self.events.append(
            {
                "type": "message",
                "sender": message.sender,
                "content": message.content[:50],
            }
        )

    def get_events(self) -> List[Dict[str, Any]]:
        """Get recorded events."""
        return self.events


# Template for creating a plugin package
PLUGIN_PACKAGE_TEMPLATE = """
# Example plugin package structure:
#
# agentmind-plugin-example/
# ├── setup.py
# ├── README.md
# ├── agentmind_plugin_example/
# │   ├── __init__.py
# │   └── plugin.py
#
# setup.py content:

from setuptools import setup, find_packages

setup(
    name="agentmind-plugin-example",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "agentmind>=0.2.0",
    ],
    entry_points={
        "agentmind.plugins.llm": [
            "example = agentmind_plugin_example.plugin:ExampleLLMProvider",
        ],
    },
)

# After installation, the plugin will be auto-discovered by AgentMind
"""


def print_plugin_template():
    """Print plugin package template."""
    print(PLUGIN_PACKAGE_TEMPLATE)
