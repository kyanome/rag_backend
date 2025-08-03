"""Test main FastAPI application."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient) -> None:
    """Test root endpoint returns correct response."""
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "RAG Backend API", "version": "0.1.0"}


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    """Test health check endpoint returns healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
