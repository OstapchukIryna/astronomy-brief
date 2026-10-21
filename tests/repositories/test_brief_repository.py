from dataclasses import replace

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.facts import Facts, InvalidFactsError
from app.models import BriefRecord
from app.repositories.brief import SqlBriefRepository
from tests.fakes import ENTRY


async def test_returns_none_for_unknown_date(session: AsyncSession) -> None:
    repository = SqlBriefRepository(session)

    assert await repository.get_by_date(ENTRY.date) is None


async def test_finds_inserted_entry_by_date(session: AsyncSession) -> None:
    repository = SqlBriefRepository(session)

    await repository.insert_if_absent(ENTRY)
    brief = await repository.get_by_date(ENTRY.date)

    assert brief is not None
    assert brief.entry == ENTRY
    assert brief.simple_explanation is None
    assert brief.facts is None


async def test_insert_if_absent_keeps_existing_brief(session: AsyncSession) -> None:
    repository = SqlBriefRepository(session)
    await repository.insert_if_absent(ENTRY)

    await repository.insert_if_absent(replace(ENTRY, title="Another title"))
    brief = await repository.get_by_date(ENTRY.date)

    assert brief is not None
    assert brief.entry.title == ENTRY.title


async def test_sets_explanation_when_absent(session: AsyncSession) -> None:
    briefs = SqlBriefRepository(session)
    await briefs.insert_if_absent(ENTRY)

    await briefs.set_explanation_if_absent(ENTRY.date, "A star is fading.")

    brief = await briefs.get_by_date(ENTRY.date)
    assert brief is not None
    assert brief.simple_explanation == "A star is fading."


async def test_keeps_existing_explanation(session: AsyncSession) -> None:
    briefs = SqlBriefRepository(session)
    await briefs.insert_if_absent(ENTRY)
    await briefs.set_explanation_if_absent(ENTRY.date, "First")

    await briefs.set_explanation_if_absent(ENTRY.date, "Second")

    brief = await briefs.get_by_date(ENTRY.date)
    assert brief is not None
    assert brief.simple_explanation == "First"


async def test_sets_facts_when_absent(session: AsyncSession) -> None:
    briefs = SqlBriefRepository(session)
    await briefs.insert_if_absent(ENTRY)

    await briefs.set_facts_if_absent(
        ENTRY.date, Facts(("It is red.", "It is fading.", "It is far."))
    )

    brief = await briefs.get_by_date(ENTRY.date)
    assert brief is not None
    assert brief.facts == Facts(("It is red.", "It is fading.", "It is far."))


async def test_keeps_existing_facts(session: AsyncSession) -> None:
    briefs = SqlBriefRepository(session)
    await briefs.insert_if_absent(ENTRY)
    await briefs.set_facts_if_absent(ENTRY.date, Facts(("First.", "A.", "B.")))

    await briefs.set_facts_if_absent(ENTRY.date, Facts(("Second.", "C.", "D.")))

    brief = await briefs.get_by_date(ENTRY.date)
    assert brief is not None
    assert brief.facts == Facts(("First.", "A.", "B."))


async def test_refuses_to_read_facts_that_break_the_rule(
    session: AsyncSession,
) -> None:
    briefs = SqlBriefRepository(session)
    await briefs.insert_if_absent(ENTRY)
    await session.execute(
        update(BriefRecord)
        .where(BriefRecord.date == ENTRY.date)
        .values(facts=["Only one."])
    )

    with pytest.raises(InvalidFactsError):
        await briefs.get_by_date(ENTRY.date)
