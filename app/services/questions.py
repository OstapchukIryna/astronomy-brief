"""Answer readers' questions about a day's picture."""

import datetime as dt

from app.domain.llm import QuestionLlm
from app.domain.questions import OffTopicQuestionError, Question
from app.services.entries import EntryStore


class QuestionService:
    """Answer questions about a day's picture. Answers are neither stored, nor cached."""

    def __init__(self, entries: EntryStore, llm: QuestionLlm) -> None:
        self._entries = entries
        self._llm = llm

    async def ask(self, date: dt.date, question: Question) -> str:
        """Return the model's answer if the question is about the date's picture."""
        brief = await self._entries.get_or_create(date)
        if not await self._llm.is_on_topic(brief.entry, question):
            raise OffTopicQuestionError(
                "The question must be about the picture of the day."
            )
        return await self._llm.answer(brief.entry, question)
