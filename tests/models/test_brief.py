import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def test_database_rejects_unknown_media_type(session: AsyncSession) -> None:
    statement = text(
        "INSERT INTO briefs (date, title, media_type, explanation, url) "
        "VALUES ('2020-01-01', 'Title', 'gif', 'Text', 'http://example.com')"
    )

    with pytest.raises(IntegrityError):
        await session.execute(statement)
