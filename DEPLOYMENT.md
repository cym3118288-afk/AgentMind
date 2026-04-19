# AgentMind Production Deployment Guide

## Overview

This guide covers deploying AgentMind to production environments with full monitoring, observability, and scaling capabilities.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Docker Deployment](#docker-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Cloud Deployments](#cloud-deployments)
5. [Production Best Practices](#production-best-practices)
6. [Monitoring & Observability](#monitoring--observability)
7. [Scaling Strategies](#scaling-strategies)
8. [Security](#security)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

### One-Command Full Stack Deployment

```bash
# Start all services (API, Chat UI, Dashboard, Monitoring)
./start_all.sh

# Stop all services
./start_all.sh stop

# View logs
./start_all.sh logs

# Check status
./start_all.sh status

# Clean up everything
./start_all.sh clean
```

### Services Available

After deployment, access:

- **API Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Chat UI**: http://localhost:5000
- **Monitoring Dashboard**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

---

## Docker Deployment

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 10GB+ disk space

### Configuration

1. **Create environment file**:

```bash
cp .env.example .env.production
```

2. **Edit `.env.production`**:

```env
# Security
JWT_SECRET=your-secret-key-here
SESSION_SECRET=your-session-secret-here

# LLM Configuration
OLLAMA_MODEL=llama3.2
OLLAMA_HOST=http://ollama:11434

# Redis
REDIS_URL=redis://redis:6379/0

# API Configuration
LOG_LEVEL=info
ENABLE_METRICS=true
ENABLE_TRACING=true
RATE_LIMIT_PER_MINUTE=60
MAX_WORKERS=4
```

3. **Deploy**:

```bash
docker-compose -f docker-compose.production.yml up -d
```

### GPU Support

For GPU acceleration with Ollama:

```bash
# Ensure NVIDIA Docker runtime is installed
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Deploy with GPU
docker-compose -f docker-compose.production.yml up -d
```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.24+
- kubectl configured
- Helm 3.0+

### Deploy to Kubernetes

1. **Create namespace**:

```bash
kubectl create namespace agentmind
```

2. **Create secrets**:

```bash
kubectl create secret generic agentmind-secrets \
  --from-literal=jwt-secret=$(openssl rand -hex 32) \
  --from-literal=session-secret=$(openssl rand -hex 32) \
  -n agentmind
```

3. **Deploy with Helm**:

```bash
helm install agentmind ./helm/agentmind \
  --namespace agentmind \
  --values helm/agentmind/values.production.yaml
```

### Kubernetes Manifests

**deployment.yaml**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentmind-api
  namespace: agentmind
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agentmind-api
  template:
    metadata:
      labels:
        app: agentmind-api
    spec:
      containers:
      - name: api
        image: agentmind/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: redis://redis:6379/0
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: agentmind-secrets
              key: jwt-secret
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

**service.yaml**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: agentmind-api
  namespace: agentmind
spec:
  selector:
    app: agentmind-api
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: LoadBalancer
```

**ingress.yaml**:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: agentmind-ingress
  namespace: agentmind
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: agentmind-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: agentmind-api
            port:
              number: 8000
```

---

## Cloud Deployments

### AWS Deployment

#### Using ECS Fargate

```bash
# Install AWS CLI and configure
aws configure

# Create ECR repository
aws ecr create-repository --repository-name agentmind-api

# Build and push image
docker build -t agentmind-api -f Dockerfile.production .
docker tag agentmind-api:latest <account-id>.dkr.ecr.<region>.amazonaws.com/agentmind-api:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/agentmind-api:latest

# Deploy with CloudFormation
aws cloudformation create-stack \
  --stack-name agentmind \
  --template-body file://aws/cloudformation.yaml \
  --parameters ParameterKey=ImageUri,ParameterValue=<ecr-image-uri>
```

#### Using Lambda (Serverless)

```bash
# Install Serverless Framework
npm install -g serverless

# Deploy
cd serverless/
serverless deploy --stage production
```

### GCP Deployment

#### Using Cloud Run

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/<project-id>/agentmind-api

# Deploy to Cloud Run
gcloud run deploy agentmind-api \
  --image gcr.io/<project-id>/agentmind-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 10
```

### Railway Deployment

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

### Vercel Deployment (Serverless)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod
```

---

## Production Best Practices

### 1. Security

- **Use HTTPS**: Always use TLS/SSL in production
- **Rotate secrets**: Regularly rotate JWT secrets and API keys
- **Enable authentication**: Implement proper JWT authentication
- **Rate limiting**: Configure appropriate rate limits
- **Input validation**: Validate all user inputs
- **PII detection**: Enable guardrails for sensitive data

### 2. Performance

- **Connection pooling**: Use Redis connection pooling
- **Caching**: Implement response caching where appropriate
- **Async operations**: Use async/await for I/O operations
- **Load balancing**: Deploy multiple API instances
- **CDN**: Use CDN for static assets

### 3. Reliability

- **Health checks**: Implement comprehensive health checks
- **Graceful shutdown**: Handle SIGTERM signals properly
- **Circuit breakers**: Implement circuit breakers for external services
- **Retries**: Use exponential backoff for retries
- **Timeouts**: Set appropriate timeouts for all operations

### 4. Observability

- **Structured logging**: Use JSON logging format
- **Distributed tracing**: Enable OpenTelemetry tracing
- **Metrics**: Export Prometheus metrics
- **Alerting**: Set up alerts for critical metrics
- **Error tracking**: Use Sentry or similar for error tracking

---

## Monitoring & Observability

### OpenTelemetry Integration

The API server includes built-in OpenTelemetry support:

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Automatic instrumentation
FastAPIInstrumentor.instrument_app(app)
```

### Langfuse Integration

For LLM observability:

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="your-public-key",
    secret_key="your-secret-key"
)

# Track LLM calls
trace = langfuse.trace(name="collaboration")
```

### Prometheus Metrics

Access metrics at `/metrics`:

- `agentmind_requests_total`: Total requests
- `agentmind_request_duration_seconds`: Request duration
- `agentmind_active_sessions`: Active sessions
- `agentmind_tokens_total`: Token usage
- `agentmind_errors_total`: Error count

### Grafana Dashboards

Pre-configured dashboards available in `monitoring/grafana/dashboards/`:

- **Overview**: System health and key metrics
- **Performance**: Response times and throughput
- **Cost Tracking**: Token usage and cost analysis
- **Errors**: Error rates and types

---

## Scaling Strategies

### Horizontal Scaling

```bash
# Docker Compose
docker-compose -f docker-compose.production.yml up -d --scale api=5

# Kubernetes
kubectl scale deployment agentmind-api --replicas=5 -n agentmind
```

### Auto-scaling (Kubernetes)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agentmind-api-hpa
  namespace: agentmind
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agentmind-api
  minReplicas: 2
  maxReplicas: 10
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
```

### Database Scaling

- **Redis Cluster**: Use Redis Cluster for high availability
- **Read Replicas**: Set up read replicas for read-heavy workloads
- **Sharding**: Implement sharding for large datasets

---

## Security

### SSL/TLS Configuration

```bash
# Generate self-signed certificate (development)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem

# Production: Use Let's Encrypt
certbot certonly --standalone -d yourdomain.com
```

### Secrets Management

#### Using Docker Secrets

```bash
echo "your-secret" | docker secret create jwt_secret -
```

#### Using Kubernetes Secrets

```bash
kubectl create secret generic agentmind-secrets \
  --from-literal=jwt-secret=$(openssl rand -hex 32) \
  -n agentmind
```

#### Using AWS Secrets Manager

```python
import boto3

client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='agentmind/jwt-secret')
```

---

## Troubleshooting

### Common Issues

#### 1. Ollama Connection Failed

```bash
# Check Ollama status
docker exec agentmind-ollama ollama list

# Pull model manually
docker exec agentmind-ollama ollama pull llama3.2
```

#### 2. Redis Connection Failed

```bash
# Check Redis status
docker exec agentmind-redis redis-cli ping

# View Redis logs
docker logs agentmind-redis
```

#### 3. High Memory Usage

```bash
# Check container stats
docker stats

# Adjust memory limits in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G
```

#### 4. Slow Response Times

- Check Prometheus metrics for bottlenecks
- Review dashboard for performance issues
- Scale horizontally if needed
- Optimize agent collaboration rounds

### Logs

```bash
# View all logs
docker-compose -f docker-compose.production.yml logs -f

# View specific service logs
docker-compose -f docker-compose.production.yml logs -f api

# View last 100 lines
docker-compose -f docker-compose.production.yml logs --tail=100 api
```

---

## Support

For issues and questions:

- GitHub Issues: https://github.com/cym3118288-afk/AgentMind-Framework/issues
- Documentation: https://github.com/cym3118288-afk/AgentMind-Framework
- Email: cym3118288@gmail.com

---

## License

MIT License - see LICENSE file for details
