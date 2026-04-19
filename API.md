# AgentMind API Documentation

Complete API reference for the AgentMind REST API.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API is open. For production, implement authentication using API keys or JWT tokens.

## Endpoints

### GET /

Get API information and available endpoints.

**Response:**
```json
{
  "name": "AgentMind API",
  "version": "0.3.0",
  "description": "Multi-agent collaboration framework",
  "endpoints": {
    "POST /collaborate": "Start a new collaboration",
    "GET /session/{session_id}": "Get session status",
    "GET /health": "Health check"
  }
}
```

### GET /health

Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "active_sessions": 2
}
```

### POST /collaborate

Start a multi-agent collaboration.

**Request Body:**
```json
{
  "task": "Design a REST API for a todo app",
  "agents": [
    {
      "name": "Architect",
      "role": "architect",
      "system_prompt": "You are a system architect...",
      "tools": []
    },
    {
      "name": "Developer",
      "role": "developer",
      "system_prompt": "You are a backend developer...",
      "tools": ["code_executor"]
    }
  ],
  "max_rounds": 5,
  "llm_provider": "ollama",
  "llm_model": "llama3.2",
  "temperature": 0.7,
  "stream": false,
  "enable_tracing": true
}
```

**Parameters:**
- `task` (string, required): Task description for agents
- `agents` (array, required): List of agent configurations
  - `name` (string): Agent name
  - `role` (string): Agent role
  - `system_prompt` (string, optional): Custom system prompt
  - `tools` (array, optional): Available tools
- `max_rounds` (integer, 1-20): Maximum collaboration rounds (default: 5)
- `llm_provider` (string): LLM provider - "ollama", "openai", "anthropic" (default: "ollama")
- `llm_model` (string): Model name (default: "llama3.2")
- `temperature` (float, 0.0-2.0): Sampling temperature (default: 0.7)
- `stream` (boolean): Enable streaming (default: false)
- `enable_tracing` (boolean): Enable observability tracing (default: true)

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "result": "Based on our collaboration, here's the API design...",
  "rounds": 3,
  "token_usage": {
    "prompt_tokens": 1250,
    "completion_tokens": 850,
    "total_tokens": 2100
  },
  "cost_estimate": {
    "prompt_cost": 0.00125,
    "completion_cost": 0.00255,
    "total_cost": 0.0038,
    "model": "llama3.2"
  },
  "duration_ms": 15420.5
}
```

**Status Codes:**
- `200 OK`: Collaboration completed successfully
- `400 Bad Request`: Invalid request parameters
- `500 Internal Server Error`: Collaboration failed

### POST /collaborate/stream

Start a streaming multi-agent collaboration with Server-Sent Events.

**Request Body:** Same as `/collaborate`

**Response:** Server-Sent Events stream

```
data: {"event": "session_start", "session_id": "550e8400-e29b-41d4-a716-446655440000"}

data: {"event": "agent_added", "agent": "Architect"}

data: {"event": "agent_added", "agent": "Developer"}

data: {"event": "agent_message", "agent": "Architect", "content": "Let me design..."}

data: {"event": "completed", "result": "Final result..."}
```

**Event Types:**
- `session_start`: Collaboration started
- `agent_added`: Agent added to collaboration
- `agent_message`: Agent sent a message
- `tool_call`: Agent executed a tool
- `completed`: Collaboration completed
- `error`: Error occurred

### GET /session/{session_id}

Get the status of a collaboration session.

**Parameters:**
- `session_id` (string, path): Session identifier

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": null,
  "result": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "result": "Collaboration result...",
    "rounds": 3,
    "token_usage": {...},
    "cost_estimate": {...},
    "duration_ms": 15420.5
  }
}
```

**Status Values:**
- `initializing`: Session is being set up
- `running`: Collaboration in progress
- `completed`: Collaboration finished successfully
- `failed`: Collaboration failed

**Status Codes:**
- `200 OK`: Session found
- `404 Not Found`: Session not found

### DELETE /session/{session_id}

Delete a collaboration session.

**Parameters:**
- `session_id` (string, path): Session identifier

**Response:**
```json
{
  "message": "Session deleted",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Status Codes:**
- `200 OK`: Session deleted
- `404 Not Found`: Session not found

### GET /sessions

List all collaboration sessions.

**Response:**
```json
{
  "total": 5,
  "sessions": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "created_at": 1234567890.123
    },
    {
      "session_id": "660e8400-e29b-41d4-a716-446655440001",
      "status": "running",
      "created_at": 1234567900.456
    }
  ]
}
```

## Examples

### Python

```python
import requests

# Start collaboration
response = requests.post(
    "http://localhost:8000/collaborate",
    json={
        "task": "Design a microservices architecture",
        "agents": [
            {"name": "Architect", "role": "architect"},
            {"name": "DevOps", "role": "devops"},
            {"name": "Security", "role": "security"}
        ],
        "max_rounds": 5,
        "llm_provider": "ollama",
        "llm_model": "llama3.2"
    }
)

result = response.json()
print(f"Session ID: {result['session_id']}")
print(f"Result: {result['result']}")
print(f"Cost: ${result['cost_estimate']['total_cost']:.4f}")
```

### JavaScript

```javascript
// Start collaboration
const response = await fetch('http://localhost:8000/collaborate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    task: 'Design a microservices architecture',
    agents: [
      { name: 'Architect', role: 'architect' },
      { name: 'DevOps', role: 'devops' },
      { name: 'Security', role: 'security' }
    ],
    max_rounds: 5,
    llm_provider: 'ollama',
    llm_model: 'llama3.2'
  })
});

const result = await response.json();
console.log('Session ID:', result.session_id);
console.log('Result:', result.result);
console.log('Cost: $', result.cost_estimate.total_cost.toFixed(4));
```

### cURL

```bash
# Start collaboration
curl -X POST http://localhost:8000/collaborate \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Design a microservices architecture",
    "agents": [
      {"name": "Architect", "role": "architect"},
      {"name": "DevOps", "role": "devops"},
      {"name": "Security", "role": "security"}
    ],
    "max_rounds": 5,
    "llm_provider": "ollama",
    "llm_model": "llama3.2"
  }'

# Get session status
curl http://localhost:8000/session/550e8400-e29b-41d4-a716-446655440000

# List all sessions
curl http://localhost:8000/sessions

# Health check
curl http://localhost:8000/health
```

### Streaming Example (Python)

```python
import requests
import json

response = requests.post(
    "http://localhost:8000/collaborate/stream",
    json={
        "task": "Design a REST API",
        "agents": [
            {"name": "Architect", "role": "architect"},
            {"name": "Developer", "role": "developer"}
        ],
        "max_rounds": 3
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith('data: '):
            data = json.loads(line[6:])
            print(f"Event: {data['event']}")
            if 'content' in data:
                print(f"Content: {data['content']}")
```

## Error Handling

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Error Codes:**
- `400 Bad Request`: Invalid input parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: LLM provider unavailable

## Rate Limiting

Currently, no rate limiting is implemented. For production:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/collaborate")
@limiter.limit("10/minute")
async def collaborate(request: Request, ...):
    ...
```

## Best Practices

1. **Use appropriate max_rounds**: Start with 3-5 rounds, increase if needed
2. **Enable tracing**: Helps debug and optimize collaborations
3. **Monitor costs**: Check `cost_estimate` in responses
4. **Handle errors**: Implement retry logic for transient failures
5. **Use streaming**: For long-running collaborations, use `/collaborate/stream`
6. **Clean up sessions**: Delete old sessions to free memory

## OpenAPI Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Support

For issues or questions:
- GitHub Issues: https://github.com/cym3118288-afk/AgentMind/issues
- Documentation: https://github.com/cym3118288-afk/AgentMind
