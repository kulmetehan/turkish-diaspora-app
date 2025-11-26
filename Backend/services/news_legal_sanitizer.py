from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from typing import Any, Dict, Iterable, List

from app.core.logging import get_logger
from app.models.news_normalized import NormalizedNewsItem

logger = get_logger().bind(module="news_legal_sanitizer")

_MAX_SNIPPET_LEN = 360
_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_IMG_TAG_PATTERN = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)


@dataclass(frozen=True)
class SanitizedNewsItem:
    title: str
    snippet: str
    url: str
    source: str
    published_at: datetime
    raw_metadata: Dict[str, Any]
    image_url: str | None = None


def _strip_html(value: str) -> str:
    text = unescape(value or "")
    text = _TAG_PATTERN.sub(" ", text)
    text = _WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()


def _trim_snippet(value: str) -> str:
    value = value.strip()
    if len(value) <= _MAX_SNIPPET_LEN:
        return value
    return value[: _MAX_SNIPPET_LEN - 1].rstrip() + "…"


def _count_tags(value: str) -> int:
    if not value:
        return 0
    return len(_TAG_PATTERN.findall(value))


def _extract_candidate_texts(raw_entry: Dict[str, Any]) -> Iterable[str]:
    keys = ("content", "summary", "description")
    for key in keys:
        value = raw_entry.get(key)
        if isinstance(value, str):
            yield value
        elif isinstance(value, list):
            for block in value:
                if isinstance(block, dict):
                    candidate = block.get("value")
                    if isinstance(candidate, str):
                        yield candidate
        elif isinstance(value, dict):
            candidate = value.get("value")
            if isinstance(candidate, str):
                yield candidate


def _looks_like_full_article(text: str) -> bool:
    if not text:
        return False
    stripped = _strip_html(text)
    if len(stripped) > 1200:
        return True
    if stripped.count(". ") > 25:
        return True
    if text.count("<p") > 5:
        return True
    return False


def _sanitize_raw_metadata(
    normalized_item: NormalizedNewsItem,
    snippet: str,
) -> Dict[str, Any]:
    return {
        "title": normalized_item.title,
        "snippet": snippet,
        "url": normalized_item.url,
        "source": normalized_item.source,
        "published_at": normalized_item.published_at.isoformat(),
    }


def sanitize_ingested_entry(
    raw_entry: Dict[str, Any] | None,
    normalized_item: NormalizedNewsItem,
    legal_profile: Dict[str, Any],
) -> SanitizedNewsItem:
    raw_entry = dict(raw_entry or {})
    candidate_texts: List[str] = list(_extract_candidate_texts(raw_entry))
    if any(_looks_like_full_article(text) for text in candidate_texts):
        logger.warning(
            "news_ingest_full_article_detected",
            source=normalized_item.source,
            url=normalized_item.url,
            legal=legal_profile,
        )

    snippet_source = normalized_item.snippet or normalized_item.title or ""
    if _count_tags(snippet_source) > 5:
        snippet_source = _strip_html(snippet_source)
    sanitized_snippet = _trim_snippet(_strip_html(snippet_source))
    if not sanitized_snippet:
        sanitized_snippet = normalized_item.title or "No summary"

    sanitized_raw_entry = _sanitize_raw_metadata(normalized_item, sanitized_snippet)
    image_url = _extract_image_url(raw_entry, candidate_texts)

    return SanitizedNewsItem(
        title=normalized_item.title,
        snippet=sanitized_snippet,
        url=normalized_item.url,
        source=normalized_item.source,
        published_at=normalized_item.published_at,
        raw_metadata=sanitized_raw_entry,
        image_url=image_url,
    )


def _extract_image_url(raw_entry: Dict[str, Any], candidate_texts: List[str]) -> str | None:
    def _extract_from_block(block: Any) -> str | None:
        if isinstance(block, dict):
            return _normalize_image_url(block.get("url") or block.get("href"))
        if isinstance(block, str):
            return _normalize_image_url(block)
        return None

    media_content = raw_entry.get("media_content")
    if isinstance(media_content, list):
        for block in media_content:
            url = _extract_from_block(block)
            if url:
                return url
    elif isinstance(media_content, dict):
        url = _extract_from_block(media_content)
        if url:
            return url

    media_thumbnail = raw_entry.get("media_thumbnail")
    if isinstance(media_thumbnail, list):
        for block in media_thumbnail:
            url = _extract_from_block(block)
            if url:
                return url
    elif isinstance(media_thumbnail, dict):
        url = _extract_from_block(media_thumbnail)
        if url:
            return url

    enclosures = raw_entry.get("enclosures")
    if isinstance(enclosures, list):
        for block in enclosures:
            url = _extract_from_block(block)
            if url:
                return url

    links = raw_entry.get("links")
    if isinstance(links, list):
        for link in links:
            if not isinstance(link, dict):
                continue
            rel = str(link.get("rel") or "").lower()
            mime = str(link.get("type") or "").lower()
            if rel == "enclosure" and ("image" in mime):
                url = _normalize_image_url(link.get("href"))
                if url:
                    return url

    fallback_fields = ("image", "picture")
    for field in fallback_fields:
        value = raw_entry.get(field)
        url = _normalize_image_url(value)
        if url:
            return url

    for text in candidate_texts:
        if not isinstance(text, str):
            continue
        match = _IMG_TAG_PATTERN.search(text)
        if match:
            url = _normalize_image_url(match.group(1))
            if url:
                return url

    return None


def _normalize_image_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if candidate.startswith("//"):
        candidate = f"https:{candidate}"
    if candidate.startswith(("http://", "https://")):
        return candidate
    return None

