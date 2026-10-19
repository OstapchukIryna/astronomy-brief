import httpx
from fastapi import FastAPI, status

from app.api.dependencies import get_database


class FakeDatabase:
    def __init__(self, *, alive: bool) -> None:
        self.alive = alive

    async def ping(self, timeout: float = 3.0) -> bool:
        return self.alive


async def test_liveness_returns_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


async def test_readiness_returns_ok_when_database_answers(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    app.dependency_overrides[get_database] = lambda: FakeDatabase(alive=True)

    response = await client.get("/health/ready")

    assert response.status_code == status.HTTP_200_OK


async def test_readiness_returns_503_when_database_is_down(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    app.dependency_overrides[get_database] = lambda: FakeDatabase(alive=False)

    response = await client.get("/health/ready")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
