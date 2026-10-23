from typing import Protocol

from app.domain.apod import ApodEntry
from app.domain.facts import Facts
from app.domain.question import Question


class LlmError(Exception):
    """Base class for all LLM errors."""


class LlmUnavailableError(LlmError):
    """The LLM can't be reached or is overloaded right now."""


class LlmBadResponseError(LlmError):
    """The LLM answered, but not with what asked for."""


class BriefLlm(Protocol):
    """What the brief service needs from a language model."""

    async def explain(self, entry: ApodEntry) -> str: ...

    async def extract_facts(self, entry: ApodEntry) -> Facts: ...


class QuestionLlm(Protocol):
    """What the question service needs from a language model."""

    async def is_on_topic(self, entry: ApodEntry, question: Question) -> bool: ...

    """Return False only for questions unrelated to astronomy."""

    async def answer(self, entry: ApodEntry, question: Question) -> str: ...


class LlmClient(BriefLlm, QuestionLlm, Protocol):
    """A language model client that serves both services."""
