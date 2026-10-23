from typing import Protocol

from app.domain.apod import ApodEntry
from app.domain.facts import Facts
from app.domain.questions import Question


class LlmError(Exception):
    """Base class for all LLM errors."""


class LlmUnavailableError(LlmError):
    """The LLM can't be reached or is overloaded right now."""


class LlmBadResponseError(LlmError):
    """The LLM answered, but not with what asked for."""


class LlmClient(Protocol):
    async def explain(self, entry: ApodEntry) -> str: ...

    async def extract_facts(self, entry: ApodEntry) -> Facts: ...

    async def is_on_topec(self, entry: ApodEntry, question: Question) -> bool: ...

    async def answer(self, entry: ApodEntry, question: Question) -> str: ...
