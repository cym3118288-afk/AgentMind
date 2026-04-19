# Docker Deployment Guide

This guide covers deploying AgentMind using Docker with integrated Ollama support.

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start the service
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop the service
docker-compose down
```

The API will be available at:
- AgentMind API: http://localhost:8000
- Ollama API: http://localhost:11434
- API Documentation: http://localhost:8000/docs

### Using Docker Directly

```bash
# Build the image
docker build -t agentmind:latest .

# Run in API mode
docker run -d \
  -p 8000:8000 \
  -p 11434:11434 \
  -e MODE=api \
  -e OLLAMA_MODEL=llama3.2 \
  --name agentmind \
  agentmind:latest

# Check health
curl http://localhost:8000/health
```

## Configuration

### Environment Variables

- `MODE`: Operation mode (`api` or `cli`)
- `OLLAMA_MODEL`: Default Ollama model to pull (default: `llama3.2`)
- `OLLAMA_HOST`: Ollama server URL (default: `http://localhost:11434`)

### Custom Models

To use a different model:

```bash
docker-compose up -d
docker exec -it agentmind-api ollama pull mistral
```

Or set in docker-compose.yml:

```yaml
environment:
  - OLLAMA_MODEL=mistral
```

## API Usage

### Start a Collaboration

```bash
curl -X POST http://localhost:8000/collaborate \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Design a REST API for a todo app",
    "agents": [
      {"name": "Architect", "role": "System architect"},
      {"name": "Developer", "role": "Backend developer"},
      {"name": "Reviewer", "role": "Code reviewer"}
    ],
    "max_rounds": 5,
    "llm_provider": "ollama",
    "llm_model": "llama3.2"
  }'
```

### Check Health

```bash
curl http://localhost:8000/health
```

### List Sessions

```bash
curl http://localhost:8000/sessions
```

## Production Deployment

### With Persistent Storage

```yaml
version: '3.8'

services:
  agentmind-api:
    build: .
    ports:
      - "8000:8000"
      - "11434:11434"
    environment:
      - MODE=api
      - OLLAMA_MODEL=llama3.2
    volumes:
      - ollama-data:/root/.ollama
      - ./traces:/app/traces
      - ./logs:/app/logs
    restart: unless-stopped

volumes:
  ollama-data:
```

### Behind a Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name agentmind.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # For streaming endpoints
    location /collaborate/stream {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
    }
}
```

### With SSL (Let's Encrypt)

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d agentmind.example.com

# Auto-renewal is configured automatically
```

## Monitoring

### Health Checks

The container includes a health check that runs every 30 seconds:

```bash
# Check container health
docker ps

# View health check logs
docker inspect --format='{{json .State.Health}}' agentmind-api | jq
```

### Logs

```bash
# View all logs
docker-compose logs -f

# View only API logs
docker-compose logs -f agentmind-api

# View last 100 lines
docker-compose logs --tail=100 agentmind-api
```

### Metrics

Access metrics endpoint:

```bash
curl http://localhost:8000/metrics
```

## Troubleshooting

### Ollama Not Starting

If Ollama fails to start:

```bash
# Check Ollama logs
docker exec -it agentmind-api journalctl -u ollama

# Restart Ollama
docker exec -it agentmind-api pkill ollama
docker exec -it agentmind-api ollama serve &
```

### Model Download Issues

If model download fails:

```bash
# Pull model manually
docker exec -it agentmind-api ollama pull llama3.2

# Check available models
docker exec -it agentmind-api ollama list
```

### Port Conflicts

If ports 8000 or 11434 are already in use:

```yaml
# Change ports in docker-compose.yml
ports:
  - "8080:8000"  # Use 8080 instead of 8000
  - "11435:11434"  # Use 11435 instead of 11434
```

### Memory Issues

For large models, increase Docker memory:

```bash
# Docker Desktop: Settings > Resources > Memory
# Or use docker-compose:
services:
  agentmind-api:
    deploy:
      resources:
        limits:
          memory: 8G
```

## Scaling

### Multiple Replicas

```yaml
version: '3.8'

services:
  agentmind-api:
    build: .
    deploy:
      replicas: 3
    ports:
      - "8000-8002:8000"
```

### Load Balancing

Use Nginx or HAProxy to load balance across replicas:

```nginx
upstream agentmind {
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
}

server {
    listen 80;
    location / {
        proxy_pass http://agentmind;
    }
}
```

## Security

### API Authentication

Add authentication middleware:

```python
# In api_server.py
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/collaborate")
async def collaborate(
    request: CollaborationRequest,
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    # Validate token
    if credentials.credentials != os.getenv("API_TOKEN"):
        raise HTTPException(status_code=401, detail="Invalid token")
    # ... rest of code
```

### Network Isolation

```yaml
services:
  agentmind-api:
    networks:
      - internal
    ports:
      - "8000:8000"

networks:
  internal:
    driver: bridge
```

## Updates

### Updating the Image

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Rolling Updates

```bash
# Build new image
docker build -t agentmind:v2 .

# Update docker-compose.yml to use new tag
# Then:
docker-compose up -d
```

## Backup and Restore

### Backup Ollama Models

```bash
# Backup volume
docker run --rm \
  -v agentmind_ollama-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/ollama-backup.tar.gz /data
```

### Restore Ollama Models

```bash
# Restore volume
docker run --rm \
  -v agentmind_ollama-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/ollama-backup.tar.gz -C /
```

## Performance Tuning

### Optimize for CPU

```yaml
services:
  agentmind-api:
    deploy:
      resources:
        limits:
          cpus: '4'
```

### Optimize for GPU

```yaml
services:
  agentmind-api:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/cym3118288-afk/AgentMind/issues
- Documentation: https://github.com/cym3118288-afk/AgentMind
