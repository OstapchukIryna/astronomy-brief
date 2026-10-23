import pytest

from app.domain.questions import InvalidQuestionError, Question


def test_trims_the_ends() -> None:
    question = Question("\t What is Betelgeuse? \n")

    assert question.text == "What is Betelgeuse?"


def test_keeps_case_and_inner_spaces() -> None:
    assert Question("What   IS it?").text == "What   IS it?"


def test_keeps_non_ascii_text() -> None:
    assert Question("Что это?").text == "Что это?"


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("abc", id="3-characters"),
        pytest.param("abcd", id="4-characters"),
        pytest.param("a" * 299, id="299-characters"),
        pytest.param("a" * 300, id="300-characters"),
    ],
)
def test_accepts_3_to_300_characters(text: str) -> None:
    assert Question(text).text == text


def test_counts_length_after_trimming() -> None:
    question = Question("  " + "a" * 300 + "\n")

    assert question.text == "a" * 300


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("ab", id="2-characters"),
        pytest.param("a" * 301, id="301-characters"),
        pytest.param("  ab  ", id="short-after-trimming"),
        pytest.param("", id="empty"),
        pytest.param("   \n\t ", id="whitespace-only"),
        pytest.param("Why\x00is it red?", id="control-character"),
        pytest.param("Why\x1bis it red?", id="escape-character"),
    ],
)
def test_rejects_questions_that_break_the_rule(text: str) -> None:
    with pytest.raises(InvalidQuestionError, match="3 to 300 characters long"):
        Question(text)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("What is it?\nAnd why is it red?", id="line-break"),
        pytest.param("What is it?\r\nAnd why is it red?", id="windows-line-break"),
        pytest.param("What is it?\tWhy red?", id="tab"),
    ],
)
def test_keeps_tabs_and_line_breaks_inside(text: str) -> None:
    assert Question(text).text == text
