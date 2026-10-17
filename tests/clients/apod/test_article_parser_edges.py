import datetime as dt

import pytest

from app.clients.apod.article_parser import parse_article
from app.domain.apod import ApodBadResponseError

DATE = dt.date(2020, 1, 1)
IMAGE = (
    '<a href="https://example.com/hd.jpg"><img src="https://example.com/img.jpg"></a>'
)


def make_article(
    media: str = IMAGE,
    date: str = "January 1, 2020",
    credit: str | None = "Image Credit: Someone",
) -> str:
    # Build a minimal article page
    rows = f'<tr class="media-detail-hero__meta-row"><th>Date</th><td>{date}</td></tr>'
    if credit is not None:
        rows += f'<tr class="media-detail-hero__meta-row"><th>Credit</th><td>{credit}</td></tr>'
    return f"""
    <div class="hds-media-detail-hero">
      <div class="media-detail-hero__media">{media}</div>
      <h1>Title</h1>
      <p class="media-detail-hero__description"><strong>Explanation:</strong> Text.</p>
      <table class="media-detail-hero__meta-table">{rows}</table>
    </div>
    """


@pytest.mark.parametrize(
    ("html", "error"),
    [
        pytest.param(make_article(media=""), "no supported media", id="no-media"),
        pytest.param(
            make_article(media='<img alt="x">'),
            "no usable 'src'",
            id="image-without-src",
        ),
        pytest.param(
            make_article(date="1st of January"),
            "Unexpected date format",
            id="malformed-date",
        ),
        pytest.param(
            make_article().replace("<th>Date</th>", "<th>Published</th>"),
            "has no date",
            id="no-date",
        ),
    ],
)
def test_rejects_malformed_article(html: str, error: str) -> None:
    with pytest.raises(ApodBadResponseError, match=error):
        parse_article(html, expected_date=DATE)


def test_credit_is_optional() -> None:
    assert parse_article(make_article(credit=None), expected_date=DATE).credit is None


def test_hd_url_is_optional_for_image_without_link() -> None:
    html = make_article(media='<img src="https://example.com/img.jpg">')

    entry = parse_article(html, expected_date=DATE)

    assert entry.hd_url is None
