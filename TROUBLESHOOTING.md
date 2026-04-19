# Troubleshooting Guide

Common issues and solutions for AgentMind framework.

## Table of Contents

- [Installation Issues](#installation-issues)
- [LLM Provider Issues](#llm-provider-issues)
- [Collaboration Issues](#collaboration-issues)
- [Memory Issues](#memory-issues)
- [Performance Issues](#performance-issues)
- [Docker Issues](#docker-issues)

## Installation Issues

### ImportError: No module named 'agentmind'

**Problem**: Cannot import agentmind after installation.

**Solution**:
```bash
# Install in editable mode
pip install -e .

# Or verify PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Dependency conflicts

**Problem**: Conflicting package versions.

**Solution**:
```bash
# Use a fresh virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

## LLM Provider Issues

### Ollama connection refused

**Problem**: `ConnectionError: Cannot connect to Ollama at http://localhost:11434`

**Solutions**:

1. **Check if Ollama is running**:
```bash
# Start Ollama
ollama serve

# Or check status
curl http://localhost:11434/api/tags
```

2. **Verify model is pulled**:
```bash
ollama list
ollama pull llama3.2
```

3. **Check custom host**:
```python
from agentmind.llm import OllamaProvider

# If Ollama runs on different host/port
llm = OllamaProvider(
    model="llama3.2",
    base_url="http://192.168.1.100:11434"
)
```

### LiteLLM API key errors

**Problem**: `AuthenticationError: Invalid API key`

**Solutions**:

1. **Set environment variables**:
```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Or in Python
import os
os.environ["OPENAI_API_KEY"] = "sk-..."
```

2. **Pass directly to provider**:
```python
from agentmind.llm import LiteLLMProvider

llm = LiteLLMProvider(
    model="gpt-4o-mini",
    api_key="sk-..."
)
```

### Model not found

**Problem**: `Model 'xyz' not found`

**Solutions**:

1. **For Ollama - pull the model**:
```bash
ollama pull llama3.2
ollama list  # Verify it's available
```

2. **For LiteLLM - check model name**:
```python
# Correct model names
"gpt-4o-mini"  # Not "gpt-4-mini"
"claude-3-5-sonnet-20241022"  # Full version
"gemini-1.5-flash"  # Not "gemini-flash"
```

### Timeout errors

**Problem**: LLM requests timing out.

**Solutions**:

1. **Increase timeout**:
```python
from agentmind.llm import OllamaProvider

llm = OllamaProvider(
    model="llama3.2",
    timeout=60.0  # Increase from default 30s
)
```

2. **Use smaller model**:
```python
# Instead of llama3.1:70b
llm = OllamaProvider(model="llama3.2")  # 3B params, much faster
```

## Collaboration Issues

### Agents not responding

**Problem**: Collaboration returns empty or no responses.

**Solutions**:

1. **Check agent is active**:
```python
agent = Agent(name="test", role="analyst")
print(agent.is_active)  # Should be True
```

2. **Verify LLM provider is set**:
```python
# Set provider on AgentMind
mind = AgentMind(llm_provider=llm)

# Or on individual agents
agent.llm_provider = llm
```

3. **Enable use_llm flag**:
```python
# For older code that uses this flag
result = await mind.start_collaboration(
    task="Analyze this",
    use_llm=True  # Make sure this is True
)
```

### Infinite loops

**Problem**: Collaboration never stops.

**Solutions**:

1. **Set max_rounds**:
```python
result = await mind.collaborate(
    task="Solve this",
    max_rounds=5  # Limit rounds
)
```

2. **Add stop condition**:
```python
def should_stop(result):
    return "DONE" in result.final_output

result = await mind.collaborate(
    task="Solve this",
    max_rounds=10,
    stop_condition=should_stop
)
```

### Duplicate agent names

**Problem**: `ValueError: Agent with name 'X' already exists`

**Solution**:
```python
# Use unique names
mind.add_agent(Agent(name="analyst_1", role="analyst"))
mind.add_agent(Agent(name="analyst_2", role="analyst"))

# Or remove existing agent first
mind.remove_agent("analyst")
mind.add_agent(Agent(name="analyst", role="analyst"))
```

## Memory Issues

### Memory growing too large

**Problem**: Agent memory consuming too much RAM.

**Solutions**:

1. **Set memory limits**:
```python
agent = Agent(name="analyst", role="analyst")
agent.config.max_memory_size = 20  # Keep last 20 messages
```

2. **Use persistent backend**:
```python
from agentmind.memory import SQLiteBackend

# Store in database instead of RAM
memory = SQLiteBackend(db_path="./agentmind.db")
```

3. **Clear old sessions**:
```python
# Periodically clear old data
mind.conversation_history.clear()
for agent in mind.agents:
    agent.memory.clear()
```

### Session not persisting

**Problem**: Sessions lost after restart.

**Solutions**:

1. **Use persistent memory backend**:
```python
from agentmind.memory import JsonFileBackend

memory = JsonFileBackend(path="./sessions")
```

2. **Save sessions explicitly**:
```python
# Save after collaboration
session_id = await mind.save_session()
print(f"Session saved: {session_id}")

# Load later
await mind.load_session(session_id)
```

## Performance Issues

### Slow response times

**Problem**: Collaboration takes too long.

**Solutions**:

1. **Use faster model**:
```python
# Instead of llama3.1:70b
llm = OllamaProvider(model="llama3.2")  # Much faster
```

2. **Reduce rounds**:
```python
result = await mind.collaborate(task, max_rounds=2)  # Instead of 5+
```

3. **Use broadcast strategy**:
```python
# Parallel execution
mind = AgentMind(strategy=CollaborationStrategy.BROADCAST)
```

4. **Enable streaming** (if supported):
```python
llm = OllamaProvider(model="llama3.2", stream=True)
```

See [PERFORMANCE.md](PERFORMANCE.md) for detailed optimization guide.

### High memory usage

**Problem**: Process using too much RAM.

**Solutions**:

1. **Limit agent memory**:
```python
for agent in mind.agents:
    agent.config.max_memory_size = 10
```

2. **Use smaller model**:
```bash
# Instead of 70B model
ollama pull llama3.2  # 3B params
```

3. **Reduce concurrent requests**:
```python
# Process in batches instead of all at once
import asyncio

async def process_batch(tasks, batch_size=5):
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        results = await asyncio.gather(*[
            mind.collaborate(task) for task in batch
        ])
        yield results
```

## Docker Issues

### Container won't start

**Problem**: Docker container exits immediately.

**Solutions**:

1. **Check logs**:
```bash
docker-compose logs agentmind
docker-compose logs ollama
```

2. **Verify Ollama is ready**:
```bash
# Wait for Ollama to start
docker-compose up -d ollama
sleep 10
docker-compose up agentmind
```

3. **Check port conflicts**:
```bash
# If port 8000 is in use
docker-compose down
# Edit docker-compose.yml to use different port
docker-compose up
```

### Model not available in container

**Problem**: Ollama model not found in Docker.

**Solution**:
```bash
# Pull model inside container
docker-compose exec ollama ollama pull llama3.2

# Or add to Dockerfile
RUN ollama pull llama3.2
```

### Cannot connect to Ollama from container

**Problem**: AgentMind container can't reach Ollama.

**Solution**:
```python
# Use service name from docker-compose.yml
llm = OllamaProvider(
    model="llama3.2",
    base_url="http://ollama:11434"  # Not localhost
)
```

## Common Error Messages

### "Agent name cannot be empty"

**Cause**: Creating agent without name.

**Fix**:
```python
# Wrong
agent = Agent(name="", role="analyst")

# Correct
agent = Agent(name="analyst", role="analyst")
```

### "max_rounds must be at least 1"

**Cause**: Invalid max_rounds value.

**Fix**:
```python
# Wrong
result = await mind.collaborate(task, max_rounds=0)

# Correct
result = await mind.collaborate(task, max_rounds=1)
```

### "No agents available"

**Cause**: Trying to collaborate without agents.

**Fix**:
```python
mind = AgentMind()
mind.add_agent(Agent(name="analyst", role="analyst"))  # Add at least one
result = await mind.collaborate(task)
```

## Getting Help

If you're still experiencing issues:

1. **Check existing issues**: [GitHub Issues](https://github.com/cym3118288-afk/AgentMind/issues)
2. **Enable debug logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```
3. **Create minimal reproduction**:
```python
# Simplest possible code that shows the issue
from agentmind import Agent, AgentMind
from agentmind.llm import OllamaProvider

llm = OllamaProvider(model="llama3.2")
mind = AgentMind(llm_provider=llm)
mind.add_agent(Agent(name="test", role="analyst"))
result = await mind.collaborate("test task")
```
4. **Open an issue** with:
   - Python version
   - AgentMind version
   - Full error traceback
   - Minimal reproduction code

## Additional Resources

- [Performance Guide](PERFORMANCE.md)
- [API Documentation](API.md)
- [Architecture Overview](ARCHITECTURE.md)
- [Examples](examples/)
