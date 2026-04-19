# Performance Optimization Guide

This guide covers best practices for optimizing AgentMind performance in production environments.

## Table of Contents

1. [LLM Provider Selection](#llm-provider-selection)
2. [Collaboration Strategies](#collaboration-strategies)
3. [Memory Management](#memory-management)
4. [Async Optimization](#async-optimization)
5. [Caching Strategies](#caching-strategies)
6. [Monitoring & Profiling](#monitoring--profiling)

## LLM Provider Selection

### Local vs Cloud Models

**Local Models (Ollama)**
- Best for: Privacy, cost control, low latency
- Trade-off: Lower quality responses
- Recommended models:
  - `llama3.2` - Fast, good quality (3B params)
  - `mistral` - Balanced performance (7B params)
  - `llama3.1:70b` - High quality, slower (70B params)

**Cloud Models (LiteLLM)**
- Best for: Highest quality, complex reasoning
- Trade-off: Cost, latency, API limits
- Recommended models:
  - `gpt-4o-mini` - Fast, cost-effective
  - `claude-3-5-sonnet` - Best quality
  - `gemini-1.5-flash` - Good balance

### Model Selection by Use Case

```python
from agentmind.llm import OllamaProvider, LiteLLMProvider

# Fast prototyping / development
dev_llm = OllamaProvider(model="llama3.2")

# Production with quality requirements
prod_llm = LiteLLMProvider(model="gpt-4o-mini")

# High-stakes decisions
critical_llm = LiteLLMProvider(model="claude-3-5-sonnet")
```

## Collaboration Strategies

### Strategy Performance Comparison

| Strategy | Speed | Quality | Use Case |
|----------|-------|---------|----------|
| Broadcast | Fast | Good | Parallel analysis, diverse perspectives |
| Round-Robin | Medium | Best | Sequential refinement, structured tasks |
| Hierarchical | Slow | Good | Complex coordination, delegation |

### Optimization Tips

**1. Use Broadcast for Independent Tasks**

```python
# Good: Parallel analysis
mind = AgentMind(strategy=CollaborationStrategy.BROADCAST)
mind.add_agent(Agent(name="sentiment", role="analyst"))
mind.add_agent(Agent(name="grammar", role="critic"))
mind.add_agent(Agent(name="style", role="creative"))

# All agents respond simultaneously
result = await mind.collaborate("Analyze this text", max_rounds=1)
```

**2. Limit Rounds for Simple Tasks**

```python
# Bad: Too many rounds for simple task
result = await mind.collaborate("Summarize this", max_rounds=10)

# Good: Appropriate rounds
result = await mind.collaborate("Summarize this", max_rounds=2)
```

**3. Use Stop Conditions**

```python
def quality_check(result):
    """Stop when quality threshold is met."""
    return "approved" in result.final_output.lower()

result = await mind.collaborate(
    task="Review this code",
    max_rounds=5,
    stop_condition=quality_check
)
```

## Memory Management

### Memory Limits

Set appropriate memory limits to prevent context overflow:

```python
from agentmind import Agent

# Limit memory to last 20 messages
agent = Agent(name="analyst", role="analyst")
agent.config.max_memory_size = 20

# Or use token-based limits
agent.config.max_memory_tokens = 4000
```

### Memory Backends

Choose the right backend for your use case:

```python
from agentmind.memory import InMemoryBackend, JsonFileBackend, SQLiteBackend

# Development: Fast, no persistence
memory = InMemoryBackend()

# Production: Persistent, simple
memory = JsonFileBackend(path="./sessions")

# Production: Persistent, queryable
memory = SQLiteBackend(db_path="./agentmind.db")
```

### Session Management

Save and restore sessions efficiently:

```python
# Save session after collaboration
session_id = await mind.save_session()

# Restore only when needed
mind = AgentMind()
await mind.load_session(session_id)
```

## Async Optimization

### Parallel Execution

Maximize throughput with proper async usage:

```python
import asyncio

# Bad: Sequential execution
results = []
for task in tasks:
    result = await mind.collaborate(task)
    results.append(result)

# Good: Parallel execution
tasks_coros = [mind.collaborate(task) for task in tasks]
results = await asyncio.gather(*tasks_coros)
```

### Timeout Management

Prevent hanging requests:

```python
from agentmind.utils import gather_with_timeout

# Set reasonable timeouts
try:
    result = await asyncio.wait_for(
        mind.collaborate(task),
        timeout=30.0  # 30 seconds
    )
except asyncio.TimeoutError:
    print("Collaboration timed out")
```

## Caching Strategies

### Agent Reuse

Reuse agents instead of recreating:

```python
# Bad: Create new agents for each request
async def handle_request(task):
    mind = AgentMind()
    mind.add_agent(Agent(name="analyst", role="analyst"))
    return await mind.collaborate(task)

# Good: Reuse agent instances
_agent_cache = {}

def get_or_create_mind():
    if "default" not in _agent_cache:
        mind = AgentMind()
        mind.add_agent(Agent(name="analyst", role="analyst"))
        _agent_cache["default"] = mind
    return _agent_cache["default"]

async def handle_request(task):
    mind = get_or_create_mind()
    return await mind.collaborate(task)
```

### Response Caching

Cache common responses:

```python
from functools import lru_cache
import hashlib

# Simple cache for identical tasks
response_cache = {}

async def cached_collaborate(mind, task):
    task_hash = hashlib.md5(task.encode()).hexdigest()
    
    if task_hash in response_cache:
        return response_cache[task_hash]
    
    result = await mind.collaborate(task)
    response_cache[task_hash] = result
    return result
```

## Monitoring & Profiling

### Cost Tracking

Monitor LLM costs in production:

```python
from agentmind.utils import CostTracker

tracker = CostTracker()

# Track collaboration costs
tracker.start()
result = await mind.collaborate(task)
tracker.end()

# Get cost summary
summary = tracker.get_summary()
print(f"Total cost: ${summary['total_cost']:.4f}")
print(f"Total tokens: {summary['total_tokens']}")
```

### Performance Tracing

Profile collaboration performance:

```python
from agentmind.utils import Tracer

tracer = Tracer(session_id="perf-test")

tracer.start()
result = await mind.collaborate(task)
tracer.end()

# Analyze performance
summary = tracer.get_summary()
print(f"Duration: {summary['duration']:.2f}s")
print(f"Rounds: {summary['rounds']}")
print(f"Messages: {summary['message_count']}")
```

### Metrics Collection

Track key metrics over time:

```python
import time

class MetricsCollector:
    def __init__(self):
        self.metrics = []
    
    async def track_collaboration(self, mind, task):
        start = time.time()
        result = await mind.collaborate(task)
        duration = time.time() - start
        
        self.metrics.append({
            "duration": duration,
            "rounds": result.rounds,
            "participants": len(result.participants),
            "timestamp": time.time()
        })
        
        return result
    
    def get_stats(self):
        if not self.metrics:
            return {}
        
        durations = [m["duration"] for m in self.metrics]
        return {
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "total_requests": len(self.metrics)
        }
```

## Best Practices Summary

1. **Choose the right model**: Local for speed, cloud for quality
2. **Optimize strategy**: Broadcast for parallel, round-robin for sequential
3. **Limit rounds**: Use stop conditions instead of high max_rounds
4. **Manage memory**: Set appropriate limits, use right backend
5. **Use async properly**: Parallel execution, timeouts
6. **Cache intelligently**: Reuse agents, cache responses
7. **Monitor performance**: Track costs, profile bottlenecks

## Performance Benchmarks

Typical performance on standard hardware (M1 Mac, 16GB RAM):

| Configuration | Latency | Throughput |
|---------------|---------|------------|
| Ollama (llama3.2) + Broadcast | 2-3s | 20 req/min |
| Ollama (llama3.2) + Round-Robin | 4-6s | 10 req/min |
| GPT-4o-mini + Broadcast | 3-5s | 15 req/min |
| GPT-4o-mini + Round-Robin | 6-10s | 6 req/min |

*Note: Actual performance varies based on task complexity and model availability.*

## Troubleshooting

### High Latency

1. Check model size (smaller = faster)
2. Reduce max_rounds
3. Use broadcast strategy
4. Enable response streaming
5. Check network latency (cloud models)

### High Memory Usage

1. Set max_memory_size limits
2. Use appropriate memory backend
3. Clear old sessions regularly
4. Reduce agent count

### High Costs

1. Use local models (Ollama)
2. Use cheaper cloud models (gpt-4o-mini)
3. Implement response caching
4. Set token limits
5. Monitor with CostTracker

## Further Reading

- [API Documentation](API.md)
- [Architecture Overview](ARCHITECTURE.md)
- [Docker Deployment](DOCKER.md)
