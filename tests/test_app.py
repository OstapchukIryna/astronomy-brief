"""Smoke test for app flow."""

import httpx
from fastapi import FastAPI, status


async def test_app_starts_and_is_ready_with_real_database(app: FastAPI) -> None:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/health/ready")

    assert response.status_code == status.HTTP_200_OK
