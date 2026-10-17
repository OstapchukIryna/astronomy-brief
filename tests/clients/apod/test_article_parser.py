import datetime as dt
from collections.abc import Callable

import pytest

from app.clients.apod.article_parser import parse_article
from app.domain.apod import ApodBadResponseError, ApodEntry, MediaType

BETELGEUSE_DATE = dt.date(2020, 1, 1)
BETELGEUSE_IMAGE_URL = (
    "https://assets.science.nasa.gov/content/dam/science/cds/apod/apod/2020/january/"
    "BetelgeuseImagined_EsoCalcada_2662.jpg?w=2662&h=4000&fit=clip&crop=faces%2Cfocalpoint"
)

EARTHSET_DATE = dt.date(2026, 4, 22)
EARTHSET_VIDEO_URL = "https://www.youtube.com/embed/MT8tg5b3b8E?feature=oembed"


@pytest.fixture
def betelgeuse(read_fixture: Callable[[str], str]) -> ApodEntry:
    return parse_article(
        read_fixture("article_image.html"), expected_date=BETELGEUSE_DATE
    )


@pytest.fixture
def earthset(read_fixture: Callable[[str], str]) -> ApodEntry:
    return parse_article(
        read_fixture("article_video.html"), expected_date=EARTHSET_DATE
    )


def test_parses_title(betelgeuse: ApodEntry) -> None:
    assert betelgeuse.title == "Betelgeuse Imagined"


def test_parses_image(betelgeuse: ApodEntry) -> None:
    assert betelgeuse.media_type == MediaType.IMAGE
    assert betelgeuse.url == BETELGEUSE_IMAGE_URL
    assert betelgeuse.hd_url == BETELGEUSE_IMAGE_URL


def test_explanation_has_no_label_prefix(betelgeuse: ApodEntry) -> None:
    assert betelgeuse.explanation.startswith("Why is Betelgeuse fading?")
    assert "Explanation:" not in betelgeuse.explanation


def test_explanation_excludes_editorial_tail(betelgeuse: ApodEntry) -> None:
    assert "Free Presentation" not in betelgeuse.explanation
    assert betelgeuse.explanation.endswith("as this new decade unfolds.")


def test_explanation_has_no_stray_spaces(betelgeuse: ApodEntry) -> None:
    assert "Betelgeuse, one of the brightest" in betelgeuse.explanation
    assert "Betelgeuse ," not in betelgeuse.explanation
    assert "(not recommended)" in betelgeuse.explanation
    assert "\n" not in betelgeuse.explanation
    assert "  " not in betelgeuse.explanation


def test_parses_video(earthset: ApodEntry) -> None:
    assert earthset.media_type == MediaType.VIDEO
    assert earthset.url == EARTHSET_VIDEO_URL
    assert earthset.hd_url is None


def test_takes_date_from_page(betelgeuse: ApodEntry) -> None:
    assert betelgeuse.date == BETELGEUSE_DATE


def test_rejects_page_for_different_date(read_fixture: Callable[[str], str]) -> None:
    html = read_fixture("article_image.html")

    with pytest.raises(ApodBadResponseError, match="expected 2001-01-01"):
        parse_article(html, expected_date=dt.date(2001, 1, 1))


def test_rejects_page_without_article_block() -> None:
    html = "<html><body>nothing here</body></html>"

    with pytest.raises(ApodBadResponseError, match="hds-media-detail-hero"):
        parse_article(html, expected_date=BETELGEUSE_DATE)


def test_image_credit_has_no_label(betelgeuse: ApodEntry) -> None:
    assert betelgeuse.credit == "ESO, L. Calcada"


def test_video_credit_has_no_label(earthset: ApodEntry) -> None:
    assert earthset.credit == (
        "NASA, Reid Wiseman Text: Keighley Rockcliffe (NASA GSFC, UMBC CSST, CRESST II)"
    )
