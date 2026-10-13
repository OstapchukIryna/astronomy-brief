from app.config import get_settings
from app.database import Database


async def test_ping_returns_true_when_database_is_reachable() -> None:
    db = Database(get_settings().database_url.get_secret_value())
    try:
        assert await db.ping() is True
    finally:
        await db.dispose()


async def test_ping_returns_false_when_database_is_unreachable() -> None:
    db = Database("postgresql+psycopg://nobody:nobody@localhost:1/nothing")
    try:
        assert await db.ping(timeout=1.0) is False
    finally:
        await db.dispose()
