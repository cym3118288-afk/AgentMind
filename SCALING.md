# AgentMind Production Scaling Guide

## Overview

This guide covers strategies for scaling AgentMind in production environments to handle increased load, improve performance, and ensure high availability.

## Scaling Dimensions

### 1. Horizontal Scaling (Scale Out)

Add more instances of services to distribute load.

#### API Server Scaling

**Docker Compose:**
```bash
docker-compose -f docker-compose.production.yml up -d --scale api=5
```

**Kubernetes:**
```bash
kubectl scale deployment agentmind-api --replicas=5 -n agentmind
```

**Auto-scaling (Kubernetes HPA):**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agentmind-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agentmind-api
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 4
        periodSeconds: 30
      selectPolicy: Max
```

### 2. Vertical Scaling (Scale Up)

Increase resources for existing instances.

**Docker Compose:**
```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

**Kubernetes:**
```yaml
resources:
  requests:
    memory: "4Gi"
    cpu: "2000m"
  limits:
    memory: "8Gi"
    cpu: "4000m"
```

### 3. Database Scaling

#### Redis Scaling

**Redis Cluster (High Availability):**
```yaml
# docker-compose.redis-cluster.yml
version: '3.8'

services:
  redis-node-1:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000 --appendonly yes
    ports:
      - "7001:6379"
    volumes:
      - redis-node-1:/data

  redis-node-2:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000 --appendonly yes
    ports:
      - "7002:6379"
    volumes:
      - redis-node-2:/data

  redis-node-3:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000 --appendonly yes
    ports:
      - "7003:6379"
    volumes:
      - redis-node-3:/data

volumes:
  redis-node-1:
  redis-node-2:
  redis-node-3:
```

**Initialize cluster:**
```bash
docker exec -it redis-node-1 redis-cli --cluster create \
  redis-node-1:6379 redis-node-2:6379 redis-node-3:6379 \
  --cluster-replicas 0
```

**Redis Sentinel (Automatic Failover):**
```yaml
services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --appendonly yes

  redis-sentinel-1:
    image: redis:7-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
    volumes:
      - ./redis/sentinel.conf:/etc/redis/sentinel.conf
```

### 4. Load Balancing

#### Nginx Load Balancer

```nginx
upstream api_backend {
    least_conn;  # Use least connections algorithm
    
    server api-1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server api-2:8000 weight=1 max_fails=3 fail_timeout=30s;
    server api-3:8000 weight=1 max_fails=3 fail_timeout=30s;
    
    keepalive 32;
}

server {
    listen 80;
    
    location /api/ {
        proxy_pass http://api_backend/;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Health check
        proxy_next_upstream error timeout http_500 http_502 http_503;
    }
}
```

#### AWS Application Load Balancer

```bash
# Create target group
aws elbv2 create-target-group \
  --name agentmind-api-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxxxx \
  --health-check-path /health \
  --health-check-interval-seconds 30

# Create load balancer
aws elbv2 create-load-balancer \
  --name agentmind-alb \
  --subnets subnet-xxxxx subnet-yyyyy \
  --security-groups sg-xxxxx
```

### 5. Caching Strategies

#### Response Caching

```python
from functools import lru_cache
import redis

redis_client = redis.Redis(host='redis', port=6379, db=0)

@lru_cache(maxsize=1000)
def get_cached_response(key: str):
    """Get cached response from Redis."""
    cached = redis_client.get(key)
    if cached:
        return cached.decode('utf-8')
    return None

def cache_response(key: str, value: str, ttl: int = 3600):
    """Cache response in Redis."""
    redis_client.setex(key, ttl, value)
```

#### CDN for Static Assets

Use CloudFlare, AWS CloudFront, or similar for static assets:

```yaml
# CloudFront distribution
Resources:
  CloudFrontDistribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Origins:
          - DomainName: api.yourdomain.com
            Id: AgentMindAPI
            CustomOriginConfig:
              HTTPPort: 80
              HTTPSPort: 443
              OriginProtocolPolicy: https-only
        Enabled: true
        DefaultCacheBehavior:
          TargetOriginId: AgentMindAPI
          ViewerProtocolPolicy: redirect-to-https
          CachePolicyId: 658327ea-f89d-4fab-a63d-7e88639e58f6
```

### 6. Database Connection Pooling

```python
from redis.connection import ConnectionPool

# Create connection pool
pool = ConnectionPool(
    host='redis',
    port=6379,
    db=0,
    max_connections=50,
    socket_timeout=5,
    socket_connect_timeout=5,
    socket_keepalive=True,
    socket_keepalive_options={
        1: 1,  # TCP_KEEPIDLE
        2: 1,  # TCP_KEEPINTVL
        3: 3   # TCP_KEEPCNT
    }
)

redis_client = redis.Redis(connection_pool=pool)
```

### 7. Async Processing with Celery

For long-running tasks:

```python
from celery import Celery

celery_app = Celery(
    'agentmind',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

@celery_app.task
def process_collaboration_async(session_id: str, request_data: dict):
    """Process collaboration asynchronously."""
    # Run collaboration
    result = run_collaboration(session_id, request_data)
    return result

# In API endpoint
@app.post("/collaborate/async")
async def collaborate_async(request: CollaborationRequest):
    session_id = str(uuid.uuid4())
    task = process_collaboration_async.delay(session_id, request.dict())
    return {"session_id": session_id, "task_id": task.id}
```

### 8. Multi-Region Deployment

#### AWS Multi-Region

```yaml
# Route 53 for DNS failover
Resources:
  HealthCheck:
    Type: AWS::Route53::HealthCheck
    Properties:
      Type: HTTPS
      ResourcePath: /health
      FullyQualifiedDomainName: api-us-east-1.yourdomain.com
      Port: 443
      RequestInterval: 30

  RecordSet:
    Type: AWS::Route53::RecordSet
    Properties:
      HostedZoneId: Z1234567890ABC
      Name: api.yourdomain.com
      Type: A
      SetIdentifier: us-east-1
      Failover: PRIMARY
      HealthCheckId: !Ref HealthCheck
      AliasTarget:
        HostedZoneId: Z1234567890ABC
        DNSName: api-us-east-1.yourdomain.com
```

### 9. Performance Optimization

#### Worker Configuration

```python
# Uvicorn with multiple workers
uvicorn.run(
    "api_server_enhanced:app",
    host="0.0.0.0",
    port=8000,
    workers=4,  # Number of worker processes
    loop="uvloop",  # Use uvloop for better performance
    log_level="info",
    access_log=False,  # Disable access log for performance
    limit_concurrency=1000,
    limit_max_requests=10000,
    timeout_keep_alive=5
)
```

#### Gunicorn Configuration

```python
# gunicorn.conf.py
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 10000
max_requests_jitter = 1000
timeout = 30
keepalive = 5
preload_app = True
```

### 10. Monitoring and Alerting

#### Prometheus Alerting Rules

```yaml
# prometheus/alerts.yml
groups:
  - name: agentmind
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(agentmind_errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(agentmind_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "P95 response time is {{ $value }}s"

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes{container="agentmind-api"} / container_spec_memory_limit_bytes{container="agentmind-api"} > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }}"
```

## Scaling Checklist

- [ ] Implement horizontal scaling with load balancer
- [ ] Configure auto-scaling based on metrics
- [ ] Set up Redis cluster for high availability
- [ ] Implement connection pooling
- [ ] Add response caching
- [ ] Configure CDN for static assets
- [ ] Set up multi-region deployment (if needed)
- [ ] Optimize worker configuration
- [ ] Implement async processing for long tasks
- [ ] Set up monitoring and alerting
- [ ] Configure rate limiting per client
- [ ] Implement circuit breakers
- [ ] Set up database read replicas
- [ ] Configure backup and disaster recovery
- [ ] Load test at expected scale

## Performance Benchmarks

Target metrics for production:

- **Response Time**: P95 < 2s, P99 < 5s
- **Throughput**: 100+ requests/second per instance
- **Error Rate**: < 0.1%
- **Availability**: 99.9% uptime
- **CPU Usage**: < 70% average
- **Memory Usage**: < 80% average

## Load Testing

```bash
# Using Apache Bench
ab -n 10000 -c 100 -H "Authorization: Bearer $TOKEN" \
  -p request.json -T application/json \
  http://localhost:8000/collaborate

# Using k6
k6 run --vus 100 --duration 5m load-test.js

# Using Locust
locust -f locustfile.py --host=http://localhost:8000
```

## Cost Optimization

1. **Use local models** (Ollama) for development and testing
2. **Implement caching** to reduce LLM API calls
3. **Use cheaper models** for simple tasks
4. **Batch requests** when possible
5. **Set token limits** to prevent runaway costs
6. **Monitor and alert** on cost thresholds
7. **Use spot instances** for non-critical workloads
8. **Implement request queuing** to smooth load

## Conclusion

Scaling AgentMind requires a multi-faceted approach combining horizontal scaling, caching, load balancing, and performance optimization. Monitor your metrics closely and scale proactively based on usage patterns.
