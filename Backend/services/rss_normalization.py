from __future__ import annotations

import calendar
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any, Dict, List, Tuple

from app.models.news_normalized import NormalizedNewsItem
from app.models.news_sources import NewsSource

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


class RSSNormalizationError(Exception):
    """
    Recoverable normalization failure for a single RSS/Atom entry.
    These errors must be logged and counted but must not abort the
    overall ingest run.
    """

    def __init__(self, message: str, entry_raw: Dict[str, Any] | None = None):
        super().__init__(message)
        self.entry_raw = entry_raw or {}


def detect_feed_type(parsed_feed: Any) -> str:
    """
    Detect the source feed format.
    Returns:
        'rss', 'atom' or 'unknown'
    """
    if isinstance(parsed_feed, dict):
        version = str(parsed_feed.get("version") or "").lower()
        feed_meta = parsed_feed.get("feed") or {}
    else:
        version = str(getattr(parsed_feed, "version", "") or "").lower()
        feed_meta = getattr(parsed_feed, "feed", {}) or {}

    if version.startswith("rss"):
        return "rss"
    if version.startswith("atom") or version == "atom10":
        return "atom"

    generator = ""
    if isinstance(feed_meta, dict):
        generator = str(feed_meta.get("generator") or "").lower()
    if "atom" in generator:
        return "atom"
    if "rss" in generator:
        return "rss"

    return "unknown"


def _struct_time_to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        timestamp = calendar.timegm(value)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except Exception:
        return None


def _strip_html(value: str) -> str:
    text = unescape(value or "")
    text = _HTML_TAG_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _trim_snippet(value: str, max_length: int = 360) -> str:
    value = value.strip()
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "…"


def _get_first_content_value(entry: Dict[str, Any]) -> str:
    content = entry.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                val = block.get("value")
                if isinstance(val, str) and val.strip():
                    return val
    if isinstance(content, dict):
        val = content.get("value")
        if isinstance(val, str):
            return val
    return ""


def _extract_rss_title(entry: Dict[str, Any]) -> str:
    title = entry.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return ""


def _extract_rss_url(entry: Dict[str, Any], fallback: str | None = None) -> str:
    link = entry.get("link")
    if isinstance(link, str) and link.strip():
        return link.strip()
    entry_id = entry.get("id")
    if isinstance(entry_id, str) and entry_id.strip():
        return entry_id.strip()
    return fallback or ""


def _extract_rss_snippet(entry: Dict[str, Any]) -> str:
    summary = entry.get("summary") or entry.get("description")
    if isinstance(summary, str) and summary.strip():
        return _trim_snippet(_strip_html(summary))
    content_value = _get_first_content_value(entry)
    if content_value:
        return _trim_snippet(_strip_html(content_value))
    title = _extract_rss_title(entry)
    if title:
        return title
    return "No summary"


def _extract_rss_published_at(entry: Dict[str, Any]) -> datetime:
    published = (
        _struct_time_to_datetime(entry.get("published_parsed"))
        or _struct_time_to_datetime(entry.get("updated_parsed"))
        or datetime.now(timezone.utc)
    )
    return published


def _extract_atom_title(entry: Dict[str, Any]) -> str:
    title = entry.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return ""


def _extract_atom_url(entry: Dict[str, Any], fallback: str | None = None) -> str:
    link = entry.get("link")
    if isinstance(link, str) and link.strip():
        return link.strip()

    links = entry.get("links")
    if isinstance(links, list):
        for link_entry in links:
            if not isinstance(link_entry, dict):
                continue
            rel = str(link_entry.get("rel") or "").lower()
            href = link_entry.get("href")
            if isinstance(href, str) and href.strip():
                if not rel or rel == "alternate":
                    return href.strip()
        for link_entry in links:
            if isinstance(link_entry, dict):
                href = link_entry.get("href")
                if isinstance(href, str) and href.strip():
                    return href.strip()

    entry_id = entry.get("id")
    if isinstance(entry_id, str) and entry_id.strip():
        return entry_id.strip()

    return fallback or ""


def _extract_atom_snippet(entry: Dict[str, Any]) -> str:
    summary = entry.get("summary")
    if isinstance(summary, str) and summary.strip():
        return _trim_snippet(_strip_html(summary))

    content_value = _get_first_content_value(entry)
    if content_value:
        return _trim_snippet(_strip_html(content_value))

    title = _extract_atom_title(entry)
    if title:
        return title

    return "No summary"


def _extract_atom_published_at(entry: Dict[str, Any]) -> datetime:
    return _extract_rss_published_at(entry)


def _build_normalized_item(
    *,
    source: NewsSource,
    title: str,
    url: str,
    snippet: str,
    published_at: datetime,
    entry: Dict[str, Any],
) -> NormalizedNewsItem:
    if not title and not url:
        raise RSSNormalizationError("missing_title_and_url", entry_raw=entry)
    return NormalizedNewsItem(
        title=title or "Untitled",
        url=url or (source.url or "#"),
        snippet=snippet or title or "No summary",
        source=source.name,
        published_at=published_at,
        raw_metadata=dict(entry),
    )


def _normalize_rss_entry(source: NewsSource, entry: Dict[str, Any]) -> NormalizedNewsItem:
    title = _extract_rss_title(entry)
    url = _extract_rss_url(entry, fallback=source.url or "#")
    snippet = _extract_rss_snippet(entry)
    published_at = _extract_rss_published_at(entry)
    return _build_normalized_item(
        source=source,
        title=title,
        url=url,
        snippet=snippet,
        published_at=published_at,
        entry=entry,
    )


def _normalize_atom_entry(source: NewsSource, entry: Dict[str, Any]) -> NormalizedNewsItem:
    title = _extract_atom_title(entry)
    url = _extract_atom_url(entry, fallback=source.url or "#")
    snippet = _extract_atom_snippet(entry)
    published_at = _extract_atom_published_at(entry)
    return _build_normalized_item(
        source=source,
        title=title,
        url=url,
        snippet=snippet,
        published_at=published_at,
        entry=entry,
    )


def normalize_entry(
    source: NewsSource,
    entry: Dict[str, Any],
    feed_type: str,
) -> Tuple[NormalizedNewsItem | None, RSSNormalizationError | None]:
    """
    Normalize a single feed entry into a NormalizedNewsItem.
    Returns:
        (NormalizedNewsItem, None) on success
        (None, RSSNormalizationError) on failure
    Implementation is split into:
        - RSS mapping (WU2)
        - Atom mapping (WU3)
    """
    try:
        if feed_type == "atom":
            item = _normalize_atom_entry(source, entry)
            return item, None

        if feed_type == "rss":
            item = _normalize_rss_entry(source, entry)
            return item, None

        # Unknown feed type: attempt RSS first, then Atom.
        rss_item: NormalizedNewsItem | None = None
        rss_error: RSSNormalizationError | None = None
        try:
            rss_item = _normalize_rss_entry(source, entry)
        except RSSNormalizationError as err:
            rss_error = err

        if rss_item:
            return rss_item, None

        try:
            atom_item = _normalize_atom_entry(source, entry)
            return atom_item, None
        except RSSNormalizationError as atom_err:
            if rss_error is not None:
                return None, rss_error
            return None, atom_err
    except RSSNormalizationError as err:
        return None, err
    except Exception as exc:
        return None, RSSNormalizationError(str(exc), entry_raw=entry)


def normalize_feed_entries(
    parsed_feed: Any,
    source: NewsSource,
) -> Tuple[List[NormalizedNewsItem], List[RSSNormalizationError]]:
    """
    Main entry point for the normalization engine.
    - Detect feed type (RSS/Atom)
    - Iterate entries safely
    - Collect normalized items + errors
    The NewsIngest pipeline will call this function in WU4.
    """
    items: List[NormalizedNewsItem] = []
    errors: List[RSSNormalizationError] = []
    if isinstance(parsed_feed, dict):
        entries = parsed_feed.get("entries") or []
    else:
        entries = getattr(parsed_feed, "entries", []) or []
    feed_type = detect_feed_type(parsed_feed)
    for entry in entries:
        item, err = normalize_entry(source, entry, feed_type)
        if item is not None:
            items.append(item)
        elif err is not None:
            errors.append(err)
    return items, errors

