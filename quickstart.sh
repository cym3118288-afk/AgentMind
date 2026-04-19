#!/bin/bash

# AgentMind Quick Start Script
# Simplified deployment for development and testing

set -e

echo "🚀 AgentMind Quick Start"
echo "========================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✓ Docker is running"

# Check if docker-compose is available
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo "❌ Docker Compose is not available"
    exit 1
fi

echo "✓ Docker Compose is available"
echo ""

# Start services
echo "📦 Starting AgentMind services..."
echo ""

$COMPOSE_CMD up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

echo ""
echo "✅ AgentMind is ready!"
echo ""
echo "📍 Access your services:"
echo "   • API Server:    http://localhost:8000"
echo "   • API Docs:      http://localhost:8000/docs"
echo "   • Chat UI:       http://localhost:5000"
echo ""
echo "📝 Useful commands:"
echo "   • View logs:     $COMPOSE_CMD logs -f"
echo "   • Stop services: $COMPOSE_CMD down"
echo "   • Restart:       $COMPOSE_CMD restart"
echo ""
echo "🎉 Happy collaborating!"
