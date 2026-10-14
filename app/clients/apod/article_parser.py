import datetime as dt
import re

from bs4 import BeautifulSoup, Tag

from app.domain.apod import ApodBadResponseError, ApodEntry, MediaType

_WHITESPACE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([,.;:!?)])")
_SPACE_AFTER_OPEN_PAREN = re.compile(r"\(\s+")
_CREDIT_LABEL = re.compile(r"^[\w\s&]*Credit[\w\s&]*:\s*")

_HERO = ".hds-media-detail-hero"
_MEDIA = ".media-detail-hero__media"
_DESCRIPTION = ".media-detail-hero__description"
_META_ROW = ".media-detail-hero__meta-row"


def _require(parent: Tag, selector: str) -> Tag:
    """Return the first element matching selector.

    Raise ApodBadResponseError if there is none.
    """
    element = parent.select_one(selector)
    if element is None:
        raise ApodBadResponseError(f"Article page has no element matching {selector!r}")
    return element


def _attr(tag: Tag, name: str) -> str:
    """Return a non-empty string attribute of the tag.

    Raise ApodBadResponseError if the attribute is missing, empty or not a string.
    """
    value = tag.get(name)
    if not isinstance(value, str) or not value:
        raise ApodBadResponseError(f"<{tag.name}> has no usable {name!r} attribute")
    return value


def _normalize_spaces(text: str) -> str:
    """Collapse whitespace and remove spaces around punctuation left by inline links."""
    text = _WHITESPACE.sub(" ", text).strip()
    text = _SPACE_BEFORE_PUNCTUATION.sub(r"\1", text)
    return _SPACE_AFTER_OPEN_PAREN.sub("(", text)


def _parse_media(media: Tag) -> tuple[MediaType, str, str | None]:
    """Return media type, URL and optional HD URL from the media block."""
    img = media.select_one("img")
    if img is not None:
        url = _attr(img, "src")
        link = img.find_parent("a")
        hd_url = _attr(link, "href") if link is not None else None
        return MediaType.IMAGE, url, hd_url

    iframe = media.select_one("iframe")
    if iframe is not None:
        return MediaType.VIDEO, _attr(iframe, "src"), None

    raise ApodBadResponseError("Article media block has no supported media")


def _parse_explanation(description: Tag) -> str:
    """Return the explanation text without the label and the editorial tail."""
    main_part = str(description).split("<br/><br/>", maxsplit=1)[0]
    text = _normalize_spaces(BeautifulSoup(main_part, "html.parser").get_text())
    return text.removeprefix("Explanation:").strip()


def _meta_value(hero: Tag, label: str) -> str | None:
    """Return the value of a row in the metadata, or None if there is no such row."""
    for row in hero.select(_META_ROW):
        header = row.select_one("th")
        value = row.select_one("td")
        if header is None or value is None:
            continue
        if header.get_text(strip=True) == label:
            return _normalize_spaces(value.get_text())
    return None


def _parse_date(hero: Tag, expected: dt.date) -> dt.date:
    """Return the publication date from the page; it must match the requested date.

    Raise ApodBadResponseError if the date is missing, malformed or different.
    """
    raw_date = _meta_value(hero, "Date")
    if raw_date is None:
        raise ApodBadResponseError("Article page has no date")
    try:
        page_date = dt.datetime.strptime(raw_date, "%B %d, %Y").date()
    except ValueError as error:
        raise ApodBadResponseError(f"Unexpected date format: {raw_date!r}") from error
    if page_date != expected:
        raise ApodBadResponseError(f"Article is for {page_date}, expected {expected}")
    return page_date


def _parse_credit(hero: Tag) -> str | None:
    """Return the credit line without its label, or None if the page has no credit."""
    credit = _meta_value(hero, "Credit")
    if credit is None:
        return None
    return _CREDIT_LABEL.sub("", credit)


def parse_article(html: str, expected_date: dt.date) -> ApodEntry:
    """Parse an APOD article page into an ApodEntry.

    Raise ApodBadResponseError if the page doesn't have the expected structure
    or is for a different date.
    """
    soup = BeautifulSoup(html, "html.parser")
    hero = _require(soup, _HERO)

    # Check date first, because wrong page must not be reported as a missing field
    date = _parse_date(hero, expected_date)
    title = _require(hero, "h1").get_text(strip=True)
    media_type, url, hd_url = _parse_media(_require(hero, _MEDIA))
    explanation = _parse_explanation(_require(hero, _DESCRIPTION))
    credit = _parse_credit(hero)

    return ApodEntry(
        date=date,
        title=title,
        explanation=explanation,
        media_type=media_type,
        url=url,
        hd_url=hd_url,
        credit=credit,
    )
