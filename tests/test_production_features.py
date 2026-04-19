"""
Tests for production features: authentication, rate limiting, observability.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
import time

# Skip all tests if fastapi is not installed
fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

# Import the enhanced API server
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api_server_enhanced import app, create_access_token


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_token():
    """Create test authentication token."""
    return create_access_token(data={"sub": "testuser"})


class TestAuthentication:
    """Test authentication features."""

    def test_get_token(self, client):
        """Test getting JWT token."""
        response = client.post("/auth/token?username=test&password=test")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.post(
            "/collaborate",
            json={"task": "Test task", "agents": [{"name": "Agent1", "role": "analyst"}]},
        )
        assert response.status_code == 403

    def test_protected_endpoint_with_token(self, client, auth_token):
        """Test accessing protected endpoint with valid token."""
        response = client.post(
            "/collaborate",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"task": "Test task", "agents": [{"name": "Agent1", "role": "analyst"}]},
        )
        # May fail due to missing dependencies, but should not be 403
        assert response.status_code != 403


class TestRateLimiting:
    """Test rate limiting features."""

    def test_rate_limit_exceeded(self, client, auth_token):
        """Test rate limiting."""
        # Make multiple requests quickly
        responses = []
        for _ in range(15):  # Limit is 10/minute
            response = client.post(
                "/collaborate",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={"task": "Test task", "agents": [{"name": "Agent1", "role": "analyst"}]},
            )
            responses.append(response.status_code)

        # Should have at least one 429 (Too Many Requests)
        assert 429 in responses


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_endpoint(self, client):
        """Test health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "active_sessions" in data


class TestMetrics:
    """Test metrics endpoint."""

    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics."""
        response = client.get("/metrics")
        assert response.status_code == 200
        # Should return Prometheus format
        assert b"agentmind" in response.content


class TestPIIDetection:
    """Test PII detection."""

    def test_pii_detection_email(self, client, auth_token):
        """Test email detection."""
        response = client.post(
            "/collaborate",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "task": "Contact me at test@example.com",
                "agents": [{"name": "Agent1", "role": "analyst"}],
                "enable_guardrails": True,
            },
        )
        # Should detect email in warnings
        if response.status_code == 200:
            data = response.json()
            assert len(data.get("warnings", [])) > 0


class TestStreaming:
    """Test streaming endpoints."""

    def test_streaming_endpoint(self, client, auth_token):
        """Test streaming collaboration."""
        response = client.post(
            "/collaborate/stream",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"task": "Test task", "agents": [{"name": "Agent1", "role": "analyst"}]},
            stream=True,
        )
        # Should return streaming response
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


class TestSessionManagement:
    """Test session management."""

    def test_list_sessions(self, client, auth_token):
        """Test listing sessions."""
        response = client.get("/sessions", headers={"Authorization": f"Bearer {auth_token}"})
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "sessions" in data

    def test_get_session_not_found(self, client, auth_token):
        """Test getting non-existent session."""
        response = client.get(
            "/session/nonexistent", headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404


class TestInputValidation:
    """Test input validation."""

    def test_invalid_agent_name(self, client, auth_token):
        """Test invalid agent name."""
        response = client.post(
            "/collaborate",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"task": "Test task", "agents": [{"name": "Agent@123", "role": "analyst"}]},
        )
        assert response.status_code == 422  # Validation error

    def test_task_too_long(self, client, auth_token):
        """Test task exceeding max length."""
        response = client.post(
            "/collaborate",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "task": "x" * 10000,  # Exceeds max length
                "agents": [{"name": "Agent1", "role": "analyst"}],
            },
        )
        assert response.status_code == 422

    def test_too_many_agents(self, client, auth_token):
        """Test too many agents."""
        agents = [{"name": f"Agent{i}", "role": "analyst"} for i in range(25)]
        response = client.post(
            "/collaborate",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"task": "Test task", "agents": agents},
        )
        assert response.status_code == 422


class TestCostEstimation:
    """Test cost estimation."""

    def test_cost_calculation(self, client, auth_token):
        """Test cost estimation in response."""
        response = client.post(
            "/collaborate",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "task": "Test task",
                "agents": [{"name": "Agent1", "role": "analyst"}],
                "llm_model": "gpt-3.5-turbo",
            },
        )
        if response.status_code == 200:
            data = response.json()
            assert "cost_estimate" in data
            assert "total_cost_usd" in data["cost_estimate"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
