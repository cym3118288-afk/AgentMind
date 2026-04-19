# AgentMind Quick Reference

A concise guide to common patterns, CLI commands, and code snippets for AgentMind.

## Table of Contents

- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [Common Patterns](#common-patterns)
- [CLI Commands](#cli-commands)
- [Code Snippets](#code-snippets)
- [Troubleshooting](#troubleshooting)

---

## Installation

### Quick Install

```bash
pip install agentmind
```

### Development Install

```bash
git clone https://github.com/cym3118288-afk/AgentMind-Framework.git
cd AgentMind-Framework
pip install -e .
```

### With Optional Dependencies

```bash
# LLM providers
pip install agentmind[llm]

# All integrations
pip install agentmind[all]

# Specific integrations
pip install agentmind[langchain]
pip install agentmind[llamaindex]
```

---

## Basic Usage

### Minimal Example

```python
import asyncio
from agentmind import Agent, AgentMind, AgentRole

async def main():
    mind = AgentMind()
    agent = Agent(name="Assistant", role=AgentRole.ANALYST.value)
    mind.add_agent(agent)
    result = await mind.start_collaboration("Your task here")
    print(result.final_output)

asyncio.run(main())
```

### With LLM

```python
from agentmind import Agent, AgentMind
from agentmind.llm import OllamaProvider

llm = OllamaProvider(model="llama3.2")
mind = AgentMind(llm_provider=llm)
agent = Agent(name="AI", role="assistant", llm_provider=llm)
mind.add_agent(agent)
```

---

## Common Patterns

### 1. Basic Collaboration

```python
# Create mind
mind = AgentMind()

# Add agents
mind.add_agent(Agent(name="Alice", role="analyst"))
mind.add_agent(Agent(name="Bob", role="creative"))

# Collaborate
result = await mind.start_collaboration("Task description")
print(result.final_output)
```

### 2. Hierarchical Collaboration

```python
from agentmind import CollaborationStrategy

mind = AgentMind(strategy=CollaborationStrategy.HIERARCHICAL)

# Add supervisor first
supervisor = Agent(name="Boss", role="supervisor")
mind.add_agent(supervisor)

# Add workers
worker = Agent(name="Worker", role="worker")
mind.add_agent(worker)
```

### 3. Custom Tools

```python
from agentmind.tools import tool

@tool(name="calculator", description="Perform calculations")
def calculator(expression: str) -> str:
    return str(eval(expression))

agent = Agent(name="Math", role="analyst")
agent.register_tool(calculator)
```

### 4. Memory Management

```python
# Add to memory
agent.add_to_memory("key", "value")

# Retrieve from memory
value = agent.get_from_memory("key")

# Clear memory
agent.clear_memory()
```

### 5. Event Handling

```python
def on_message(agent_name: str, message: str):
    print(f"{agent_name}: {message}")

mind.on("message", on_message)
```

### 6. Async Collaboration

```python
# Start collaboration
task = mind.start_collaboration("Task", max_rounds=5)

# Wait for completion
result = await task

# Or run multiple in parallel
results = await asyncio.gather(
    mind.start_collaboration("Task 1"),
    mind.start_collaboration("Task 2")
)
```

### 7. Error Handling

```python
try:
    result = await mind.start_collaboration("Task")
    if result.success:
        print(result.final_output)
    else:
        print(f"Failed: {result.error}")
except Exception as e:
    print(f"Error: {e}")
```

### 8. Configuration

```python
mind = AgentMind(
    strategy=CollaborationStrategy.ROUND_ROBIN,
    max_rounds=10,
    timeout=300,
    llm_provider=llm
)
```

---

## CLI Commands

### Running Examples

```bash
# Basic collaboration
python examples/basic_collaboration.py

# With specific example
python examples/debate_example.py

# Run all examples
for f in examples/*.py; do python "$f"; done
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agentmind

# Run specific test file
pytest tests/test_agent.py

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_agent.py::test_agent_creation
```

### Linting and Formatting

```bash
# Check code style
ruff check src/

# Fix auto-fixable issues
ruff check --fix src/

# Format code
ruff format src/

# Type checking
mypy src/
```

### Building and Publishing

```bash
# Build package
python -m build

# Check package
twine check dist/*

# Upload to Test PyPI
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

### Version Management

```bash
# Bump patch version (0.1.0 -> 0.1.1)
python scripts/bump_version.py patch

# Bump minor version (0.1.0 -> 0.2.0)
python scripts/bump_version.py minor

# Bump major version (0.1.0 -> 1.0.0)
python scripts/bump_version.py major

# Set custom version
python scripts/bump_version.py custom 1.5.2
```

### Release

```bash
# Automated release
./scripts/release.sh

# Manual release steps
python scripts/bump_version.py minor
pytest
python -m build
git commit -am "Release vX.Y.Z"
git tag -a vX.Y.Z -m "Release X.Y.Z"
git push --follow-tags
twine upload dist/*
```

---

## Code Snippets

### Agent Roles

```python
from agentmind import AgentRole

# Available roles
AgentRole.ANALYST      # Data analysis and insights
AgentRole.CREATIVE     # Idea generation
AgentRole.CRITIC       # Critical evaluation
AgentRole.COORDINATOR  # Facilitation and synthesis
AgentRole.RESEARCHER   # Information gathering
AgentRole.SUPERVISOR   # Team coordination
AgentRole.EXECUTOR     # Task execution
```

### Collaboration Strategies

```python
from agentmind import CollaborationStrategy

# Available strategies
CollaborationStrategy.ROUND_ROBIN    # Sequential turns
CollaborationStrategy.HIERARCHICAL   # Supervisor-led
CollaborationStrategy.CONSENSUS      # Agreement-based
CollaborationStrategy.DEBATE         # Argumentative
CollaborationStrategy.PARALLEL       # Concurrent execution
```

### LLM Providers

```python
# Ollama (local)
from agentmind.llm import OllamaProvider
llm = OllamaProvider(model="llama3.2", temperature=0.7)

# LiteLLM (cloud)
from agentmind.llm import LiteLLMProvider
llm = LiteLLMProvider(model="gpt-4", temperature=0.7)

# OpenAI
import os
os.environ["OPENAI_API_KEY"] = "your-key"
llm = LiteLLMProvider(model="gpt-3.5-turbo")
```

### Result Inspection

```python
result = await mind.start_collaboration("Task")

# Check success
if result.success:
    print("Success!")

# Get output
print(result.final_output)

# View statistics
print(f"Rounds: {result.total_rounds}")
print(f"Messages: {result.total_messages}")

# Agent contributions
for agent, count in result.agent_contributions.items():
    print(f"{agent}: {count} messages")

# Execution time
print(f"Duration: {result.duration}s")
```

### Conversation History

```python
# Get summary
summary = mind.get_conversation_summary()
print(f"Total messages: {summary['total_messages']}")
print(f"Active agents: {summary['active_agents']}")

# Get full history
history = mind.get_conversation_history()
for msg in history:
    print(f"{msg['agent']}: {msg['content']}")

# Clear history
mind.clear_conversation_history()
```

### Tool Creation

```python
from agentmind.tools import tool
from typing import List

@tool(name="search", description="Search for information")
def search(query: str, limit: int = 10) -> List[str]:
    """Search and return results."""
    # Implementation
    return ["result1", "result2"]

# With async
@tool(name="async_search", description="Async search")
async def async_search(query: str) -> str:
    """Async search implementation."""
    # Async implementation
    return "results"
```

### Custom Agent Class

```python
from agentmind import Agent

class CustomAgent(Agent):
    def __init__(self, name: str, role: str, **kwargs):
        super().__init__(name, role, **kwargs)
        self.custom_data = {}

    async def process_message(self, message: str) -> str:
        """Custom message processing."""
        # Custom logic
        response = await super().process_message(message)
        return response

    def custom_method(self):
        """Add custom functionality."""
        pass
```

### Integration Examples

```python
# LangChain
from langchain.tools import Tool
from agentmind.integrations import langchain_to_agentmind

lc_tool = Tool(name="search", func=search_func, description="Search")
am_tool = langchain_to_agentmind(lc_tool)

# LlamaIndex
from llama_index import VectorStoreIndex
from agentmind.integrations import llamaindex_query_engine

index = VectorStoreIndex.from_documents(docs)
query_engine = index.as_query_engine()
agent.register_tool(llamaindex_query_engine(query_engine))
```

---

## Troubleshooting

### Common Issues

#### Import Error

```python
# Problem: ModuleNotFoundError: No module named 'agentmind'
# Solution:
pip install agentmind
# Or for development:
pip install -e .
```

#### Ollama Connection Error

```python
# Problem: Could not connect to Ollama
# Solution:
# 1. Install Ollama: https://ollama.ai
# 2. Pull model: ollama pull llama3.2
# 3. Verify: ollama list
# 4. Or use template mode (no LLM)
```

#### Async Runtime Error

```python
# Problem: RuntimeError: asyncio.run() cannot be called from a running event loop
# Solution: Use await instead of asyncio.run()
# In Jupyter/IPython:
result = await mind.start_collaboration("Task")
# In scripts:
asyncio.run(main())
```

#### Memory Issues

```python
# Problem: High memory usage with many agents
# Solution: Clear conversation history periodically
mind.clear_conversation_history()
# Or limit history size
mind.set_max_history(100)
```

#### Timeout Errors

```python
# Problem: Collaboration times out
# Solution: Increase timeout
mind = AgentMind(timeout=600)  # 10 minutes
# Or reduce max_rounds
result = await mind.start_collaboration("Task", max_rounds=3)
```

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or for specific module
logger = logging.getLogger("agentmind")
logger.setLevel(logging.DEBUG)
```

### Performance Tips

```python
# 1. Use caching
agent.enable_cache()

# 2. Limit conversation history
mind.set_max_history(50)

# 3. Use parallel execution
mind = AgentMind(strategy=CollaborationStrategy.PARALLEL)

# 4. Optimize LLM parameters
llm = OllamaProvider(model="llama3.2", temperature=0.5, max_tokens=500)

# 5. Batch operations
results = await asyncio.gather(*[
    mind.start_collaboration(task) for task in tasks
])
```

---

## Quick Reference Card

### Essential Commands

| Action | Command |
|--------|---------|
| Install | `pip install agentmind` |
| Run example | `python examples/basic_collaboration.py` |
| Run tests | `pytest` |
| Check code | `ruff check src/` |
| Build package | `python -m build` |
| Bump version | `python scripts/bump_version.py patch` |
| Release | `./scripts/release.sh` |

### Essential Imports

```python
from agentmind import Agent, AgentMind, AgentRole, CollaborationStrategy
from agentmind.llm import OllamaProvider, LiteLLMProvider
from agentmind.tools import tool
```

### Essential Pattern

```python
import asyncio
from agentmind import Agent, AgentMind

async def main():
    mind = AgentMind()
    agent = Agent(name="AI", role="assistant")
    mind.add_agent(agent)
    result = await mind.start_collaboration("Your task")
    print(result.final_output)

asyncio.run(main())
```

---

## Resources

- **Documentation**: [GitHub README](https://github.com/cym3118288-afk/AgentMind-Framework)
- **Examples**: `examples/` directory
- **Issues**: [GitHub Issues](https://github.com/cym3118288-afk/AgentMind-Framework/issues)
- **Contributing**: See `CONTRIBUTING.md`
- **License**: See `LICENSE`

---

**Last Updated**: 2026-04-19  
**Version**: 0.1.0
