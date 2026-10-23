import unicodedata
from dataclasses import dataclass

MIN_QUESTION_LENGTH = 3
MAX_QUESTION_LENGTH = 300
ALLOWED_CONTROL_CHARACTERS = frozenset("\t\n\r")  # pasted questions may span lines


class InvalidQuestionError(ValueError):
    """A question that breaks the length or the character rule."""


class OffTopicQuestionError(ValueError):
    """The question is not about the picture of the day."""


def _has_forbidden_characters(text: str) -> bool:
    return any(
        unicodedata.category(char) == "Cc" and char not in ALLOWED_CONTROL_CHARACTERS
        for char in text
    )


@dataclass(frozen=True, slots=True)
class Question:
    """A reader's question about a day's picture."""

    text: str

    def __post_init__(self) -> None:
        text = self.text.strip()
        if not MIN_QUESTION_LENGTH <= len(
            text
        ) <= MAX_QUESTION_LENGTH or _has_forbidden_characters(text):
            raise InvalidQuestionError(
                f"The question must be {MIN_QUESTION_LENGTH} to "
                f"{MAX_QUESTION_LENGTH} characters long, without control characters."
            )
        object.__setattr__(self, "text", text)
