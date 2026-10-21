"""The facts rule: every brief has 3 to 5 distinct facts about its picture."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Self

MIN_FACTS = 3
MAX_FACTS = 5


class InvalidFactsError(ValueError):
    """Facts that break the 3 to 5 distinct facts rule."""


@dataclass(frozen=True, slots=True)
class Facts:
    """Return 3 to 5 distinct and clean facts with preserving order."""

    items: tuple[str, ...]

    def __post_init__(self) -> None:
        count = len(self.items)
        if not MIN_FACTS <= count <= MAX_FACTS:
            raise InvalidFactsError(
                f"Expected {MIN_FACTS} to {MAX_FACTS} facts, got {count}"
            )
        for item in self.items:
            if not item or item != item.strip():
                raise InvalidFactsError(
                    f"Facts must be trimmed and non-empty: {item!r}"
                )
        if len({item.casefold() for item in self.items}) != count:
            raise InvalidFactsError(
                f"Facts must be distinct, ignoring case: {self.items}"
            )

    @classmethod
    def from_candidates(cls, candidates: Iterable[str]) -> Self:
        """Clean the candidates and return the first facts that make a valid set."""
        if isinstance(candidates, str):
            raise TypeError("Expected an iterable of facts, got a single string")
        seen: set[str] = set()
        facts: list[str] = []
        for candidate in candidates:
            fact = candidate.strip()
            key = fact.casefold()
            if not fact or key in seen:
                continue
            seen.add(key)
            facts.append(fact)
        return cls(tuple(facts[:MAX_FACTS]))
