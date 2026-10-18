import datetime as dt

import pytest

from app.domain.history import (
    HistoryFilter,
    InvalidHistoryFilterError,
    PageRequest,
)

JAN_1 = dt.date(2020, 1, 1)
JAN_2 = dt.date(2020, 1, 2)


def test_filter_without_conditions_is_allowed() -> None:
    history_filter = HistoryFilter()

    assert history_filter.date_from is None
    assert history_filter.date_to is None
    assert history_filter.keyword is None


def test_rejects_start_after_end() -> None:
    with pytest.raises(InvalidHistoryFilterError, match="after"):
        HistoryFilter(date_from=JAN_2, date_to=JAN_1)


def test_accepts_single_day_range() -> None:
    history_filter = HistoryFilter(date_from=JAN_1, date_to=JAN_1)

    assert history_filter.date_from == history_filter.date_to == JAN_1


def test_strips_spaces_around_keyword() -> None:
    assert HistoryFilter(keyword="  nebula  ").keyword == "nebula"


@pytest.mark.parametrize(
    "keyword",
    [
        pytest.param("ab", id="too-short"),
        pytest.param("   ", id="blank"),
        pytest.param("  ab  ", id="short-after-strip"),
        pytest.param("x" * 101, id="too-long"),
    ],
)
def test_rejects_keyword_of_wrong_length(keyword: str) -> None:
    with pytest.raises(InvalidHistoryFilterError, match="keyword"):
        HistoryFilter(keyword=keyword)


@pytest.mark.parametrize("length", [3, 100])
def test_accepts_keyword_at_length_limits(length: int) -> None:
    keyword = "x" * length

    assert HistoryFilter(keyword=keyword).keyword == keyword


@pytest.mark.parametrize(
    "limit",
    [pytest.param(0, id="empty-page"), pytest.param(101, id="page-too-large")],
)
def test_rejects_page_outside_limits(limit: int) -> None:
    with pytest.raises(InvalidHistoryFilterError):
        PageRequest(limit=limit)


@pytest.mark.parametrize("limit", [1, 100])
def test_accepts_page_size_at_limits(limit: int) -> None:
    assert PageRequest(limit=limit).limit == limit
