from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.apod import MediaType
from app.repositories.brief import BriefRepository
from tests.fakes import ENTRY


async def test_returns_none_for_unknown_date(session: AsyncSession) -> None:
    repository = BriefRepository(session)

    assert await repository.get_by_date(ENTRY.date) is None


async def test_finds_inserted_entry_by_date(session: AsyncSession) -> None:
    repository = BriefRepository(session)

    await repository.insert_if_absent(ENTRY)
    brief = await repository.get_by_date(ENTRY.date)

    assert brief is not None
    assert brief.title == ENTRY.title
    assert brief.media_type == MediaType.IMAGE
    assert brief.simple_explanation is None


async def test_insert_if_absent_keeps_existing_brief(session: AsyncSession) -> None:
    repository = BriefRepository(session)
    await repository.insert_if_absent(ENTRY)

    await repository.insert_if_absent(replace(ENTRY, title="Another title"))
    brief = await repository.get_by_date(ENTRY.date)

    assert brief is not None
    assert brief.title == ENTRY.title


async def test_sets_explanation_when_absent(session: AsyncSession) -> None:
    briefs = BriefRepository(session)
    await briefs.insert_if_absent(ENTRY)

    await briefs.set_explanation_if_absent(ENTRY.date, "A star is fading.")

    brief = await briefs.get_by_date(ENTRY.date)
    assert brief is not None
    assert brief.simple_explanation == "A star is fading."


async def test_keeps_existing_explanation(session: AsyncSession) -> None:
    briefs = BriefRepository(session)
    await briefs.insert_if_absent(ENTRY)
    await briefs.set_explanation_if_absent(ENTRY.date, "First")

    await briefs.set_explanation_if_absent(ENTRY.date, "Second")

    brief = await briefs.get_by_date(ENTRY.date)
    assert brief is not None
    assert brief.simple_explanation == "First"


async def test_sets_facts_when_absent(session: AsyncSession) -> None:
    briefs = BriefRepository(session)
    await briefs.insert_if_absent(ENTRY)

    await briefs.set_facts_if_absent(
        ENTRY.date, ["It is red.", "It is fading.", "It is far."]
    )

    brief = await briefs.get_by_date(ENTRY.date)
    assert brief is not None
    assert brief.facts == ["It is red.", "It is fading.", "It is far."]


async def test_keeps_existing_facts(session: AsyncSession) -> None:
    briefs = BriefRepository(session)
    await briefs.insert_if_absent(ENTRY)
    await briefs.set_facts_if_absent(ENTRY.date, ["First."])

    await briefs.set_facts_if_absent(ENTRY.date, ["Second."])

    brief = await briefs.get_by_date(ENTRY.date)
    assert brief is not None
    assert brief.facts == ["First."]
