import pytest

from app.domain.facts import Facts, InvalidFactsError


@pytest.mark.parametrize(
    "candidates",
    [
        pytest.param([], id="none"),
        pytest.param(["One.", "Two."], id="two"),
        pytest.param(["Same.", "same.", "Other."], id="three-with-a-repeat"),
        pytest.param(["One.", "", "Two.", " "], id="three-with-an-empty-one"),
        pytest.param(
            ["Mars.", "mars.", "MARS.", "Venus."], id="four-with-two-distinct"
        ),
    ],
)
def test_from_candidates_rejects_fewer_than_three_distinct(
    candidates: list[str],
) -> None:
    with pytest.raises(InvalidFactsError):
        Facts.from_candidates(candidates)


@pytest.mark.parametrize(
    ("candidates", "expected"),
    [
        pytest.param(["A.", "B.", "C."], ("A.", "B.", "C."), id="three"),
        pytest.param(["A.", "B.", "C.", "D."], ("A.", "B.", "C.", "D."), id="four"),
        pytest.param(
            ["A.", "B.", "C.", "D.", "E."], ("A.", "B.", "C.", "D.", "E."), id="five"
        ),
    ],
)
def test_from_candidates_keeps_valid_facts(
    candidates: list[str], expected: tuple[str, ...]
) -> None:
    assert Facts.from_candidates(candidates).items == expected


def test_from_candidates_keeps_the_first_five() -> None:
    facts = Facts.from_candidates(["A.", "B.", "C.", "D.", "E.", "F."])

    assert facts.items == ("A.", "B.", "C.", "D.", "E.")


def test_from_candidates_strips_spaces_and_drops_empty_ones() -> None:
    facts = Facts.from_candidates(
        ["  Mars is red. ", "", "\tVenus is hot.\n", "   ", "Jupiter is big.  "]
    )

    assert facts.items == ("Mars is red.", "Venus is hot.", "Jupiter is big.")


def test_from_candidates_drops_repeats_ignoring_case() -> None:
    facts = Facts.from_candidates(
        ["It is red.", "It is fading.", "it is RED.", "It is far."]
    )

    assert facts.items == ("It is red.", "It is fading.", "It is far.")


def test_from_candidates_drops_repeats_after_trimming() -> None:
    facts = Facts.from_candidates([" Mars.", "mars.  ", "Venus.", "Jupiter."])

    assert facts.items == ("Mars.", "Venus.", "Jupiter.")


def test_from_candidates_keeps_the_given_order() -> None:
    facts = Facts.from_candidates(["C fact.", "A fact.", "B fact."])

    assert facts.items == ("C fact.", "A fact.", "B fact.")


@pytest.mark.parametrize(
    ("candidates", "expected"),
    [
        pytest.param(
            ["A.", "a.", "B.", "b.", "C.", "D.", "E.", "F."],
            ("A.", "B.", "C.", "D.", "E."),
            id="repeats",
        ),
        pytest.param(
            ["A.", "A.", "A.", "B.", "B.", "C."], ("A.", "B.", "C."), id="many-repeats"
        ),
        pytest.param(
            ["", "", "A.", "B.", "C.", "D.", "E."],
            ("A.", "B.", "C.", "D.", "E."),
            id="empties",
        ),
    ],
)
def test_from_candidates_cleans_before_cutting(
    candidates: list[str], expected: tuple[str, ...]
) -> None:
    assert Facts.from_candidates(candidates).items == expected


def test_from_candidates_accepts_a_one_pass_iterator() -> None:
    facts = Facts.from_candidates(iter(["A.", "B.", "C."]))

    assert facts.items == ("A.", "B.", "C.")


def test_facts_dont_change_with_their_source() -> None:
    source = ["A.", "B.", "C."]
    facts = Facts.from_candidates(source)

    source.append("D.")

    assert facts.items == ("A.", "B.", "C.")


def test_from_candidates_rejects_a_bare_string() -> None:
    with pytest.raises(TypeError):
        Facts.from_candidates("abc")


def test_strict_constructor_accepts_cleaned_facts() -> None:
    facts = Facts.from_candidates([" A.", "a.", "B.", "C."])

    assert Facts(facts.items) == facts


@pytest.mark.parametrize(
    "items",
    [
        pytest.param(("A.", "B.", "C."), id="three"),
        pytest.param(("A.", "B.", "C.", "D.", "E."), id="five"),
    ],
)
def test_accepts_facts_at_count_limits(items: tuple[str, ...]) -> None:
    assert Facts(items).items == items


@pytest.mark.parametrize(
    "items",
    [
        pytest.param(("One.", "Two."), id="too-few"),
        pytest.param(("A.", "B.", "C.", "D.", "E.", "F."), id="too-many"),
        pytest.param(("A.", "A.", "B.", "C."), id="exact-repeat"),
        pytest.param(("One.", "Two.", "Three.", "one."), id="repeat"),
        pytest.param(("One.", "Two.", "Three.", ""), id="empty"),
        pytest.param(("One.", "Two.", "Three.", "   "), id="whitespace-only"),
        pytest.param((" One.", "Two.", "Three."), id="untrimmed"),
    ],
)
def test_rejects_facts_that_break_the_rule(items: tuple[str, ...]) -> None:
    with pytest.raises(InvalidFactsError):
        Facts(items)


def test_facts_compare_by_value_and_order() -> None:
    assert Facts(("A.", "B.", "C.")) == Facts(("A.", "B.", "C."))
    assert Facts(("A.", "B.", "C.")) != Facts(("B.", "A.", "C."))
