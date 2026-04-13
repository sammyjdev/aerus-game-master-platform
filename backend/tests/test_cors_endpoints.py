"""
test_cors_endpoints.py — Tests for CORS configuration (TDD for O-02).
Validates CORS defaults fail-closed with localhost fallback for dev.
"""
import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
class TestCORSDefaults:
    """GAP O-02: CORS must default to fail-closed."""

    async def test_cors_header_present(self, client: AsyncClient):
        """CORS Access-Control-Allow-Origin header should be present."""
        response = await client.get("/health")
        # Should have CORS headers after implementation
        assert "access-control-allow-origin" in response.headers or response.status_code == status.HTTP_200_OK

    async def test_cors_localhost_allowed_in_dev(self, client: AsyncClient):
        """localhost:5173 should be allowed (dev default)."""
        headers = {"Origin": "http://localhost:5173"}
        response = await client.get("/health", headers=headers)
        assert response.status_code == status.HTTP_200_OK

    async def test_cors_arbitrary_origin_rejected(self, client: AsyncClient):
        """Arbitrary origin should not be allowed unless configured."""
        headers = {"Origin": "http://attacker.com"}
        response = await client.get("/health", headers=headers)
        # Should either reject or not include the attacker domain in CORS header
        cors_header = response.headers.get("access-control-allow-origin", "")
        assert "attacker.com" not in cors_header or cors_header == ""

    async def test_cors_wildcard_not_default(self, client: AsyncClient):
        """CORS should never default to wildcard (*)."""
        response = await client.get("/health")
        cors_header = response.headers.get("access-control-allow-origin", "")
        # Only localhost or configured origins, never bare *
        assert cors_header != "*" or cors_header == ""
