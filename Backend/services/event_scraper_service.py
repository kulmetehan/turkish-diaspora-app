from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import feedparser
import httpx
from dateutil import parser as date_parser
from selectolax.parser import HTMLParser, Node

from app.core.logging import get_logger
from app.models.event_raw import EventRawCreate
from app.models.event_sources import EventSource
from services.event_raw_service import insert_many_event_raw

logger = get_logger()

NL_MONTH_MAP = {
    "januari": "January",
    "februari": "February",
    "maart": "March",
    "april": "April",
    "mei": "May",
    "juni": "June",
    "juli": "July",
    "augustus": "August",
    "september": "September",
    "oktober": "October",
    "november": "November",
    "december": "December",
}

DEFAULT_JSON_LD_SCRIPT = "script[type='application/ld+json']"


@dataclass
class EventScraperResult:
    event_source_id: int
    total_items: int
    inserted: int
    errors: int
    skipped: bool = False


class EventScraperService:
    def __init__(
        self,
        *,
        timeout_s: int = 15,
        max_concurrency: int = 5,
        max_retries: int = 2,
    ) -> None:
        self.timeout_s = timeout_s
        self.max_concurrency = max(1, max_concurrency)
        self.max_retries = max(0, max_retries)
        self._client: Optional[httpx.AsyncClient] = None
        self._sem = asyncio.Semaphore(self.max_concurrency)

    async def __aenter__(self) -> "EventScraperService":
        self._client = httpx.AsyncClient(
            timeout=self.timeout_s,
            headers={"User-Agent": "tda-event-scraper/1.0"},
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client:
            await self._client.aclose()

    def should_fetch(self, source: EventSource) -> bool:
        """
        Respect interval scheduling using last_run_at/last_success_at timestamps.
        """
        reference = source.last_run_at or source.last_success_at
        if reference is None:
            return True
        next_allowed = reference + timedelta(minutes=source.interval_minutes)
        return datetime.now(timezone.utc) >= next_allowed

    async def scrape_source(self, source: EventSource) -> EventScraperResult:
        if not self.should_fetch(source):
            logger.info(
                "event_scraper_source_skipped",
                source_id=source.id,
                key=source.key,
                interval_minutes=source.interval_minutes,
            )
            return EventScraperResult(
                event_source_id=source.id,
                total_items=0,
                inserted=0,
                errors=0,
                skipped=True,
            )

        url = source.list_url or source.base_url
        try:
            response = await self._fetch(url)
        except Exception as exc:
            logger.warning(
                "event_scraper_fetch_failed",
                source_id=source.id,
                key=source.key,
                url=url,
                error=str(exc),
            )
            return EventScraperResult(
                event_source_id=source.id,
                total_items=0,
                inserted=0,
                errors=1,
            )

        try:
            events = self._parse_response(source, response)
        except Exception as exc:
            logger.warning(
                "event_scraper_parse_failed",
                source_id=source.id,
                key=source.key,
                error=str(exc),
            )
            return EventScraperResult(
                event_source_id=source.id,
                total_items=0,
                inserted=0,
                errors=1,
            )

        inserted = await insert_many_event_raw(events)
        logger.info(
            "event_scraper_source_success",
            source_id=source.id,
            key=source.key,
            inserted=inserted,
            total=len(events),
        )
        return EventScraperResult(
            event_source_id=source.id,
            total_items=len(events),
            inserted=inserted,
            errors=0,
        )

    async def _fetch(self, url: str) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("EventScraperService HTTP client not initialized")
        attempt = 0
        delay = 1.0
        last_exc: Optional[Exception] = None
        while attempt <= self.max_retries:
            try:
                async with self._sem:
                    response = await self._client.get(url)
                response.raise_for_status()
                return response
            except Exception as exc:
                last_exc = exc
                attempt += 1
                if attempt > self.max_retries:
                    break
                await asyncio.sleep(delay)
                delay = min(delay * 2, 10)
        assert last_exc is not None
        raise last_exc

    def _parse_response(self, source: EventSource, response: httpx.Response) -> List[EventRawCreate]:
        fmt = source.selectors.get("format", "html")
        if fmt == "html":
            return self._parse_html_events(source, response.text)
        if fmt == "rss":
            return self._parse_rss_events(source, response.text)
        if fmt == "json":
            try:
                payload = response.json()
            except Exception as exc:  # pragma: no cover - defensive
                raise ValueError(f"Invalid JSON payload: {exc}") from exc
            return self._parse_json_events(source, payload)
        if fmt == "json_ld":
            return self._parse_json_ld_events(source, response.text)
        raise ValueError(f"Unsupported selector format: {fmt}")

    def _parse_html_events(self, source: EventSource, html_text: str) -> List[EventRawCreate]:
        selectors = source.selectors
        parser = HTMLParser(html_text)
        nodes = parser.css(selectors["item_selector"])
        time_selector = selectors.get("time_selector")
        timezone_name = selectors.get("timezone")
        datetime_format = selectors.get("datetime_format")
        locale_hint = selectors.get("locale")
        events: List[EventRawCreate] = []
        for node in nodes:
            title = self._extract_node_value(node, selectors.get("title_selector"))
            if not title:
                continue
            url_value = self._extract_node_value(node, selectors.get("url_selector"))
            full_url = self._absolutize_url(source, url_value)
            description = self._extract_node_value(node, selectors.get("description_selector"))
            location_text = self._extract_node_value(node, selectors.get("location_selector"))
            venue = self._extract_node_value(node, selectors.get("venue_selector"))
            image_url = self._extract_node_value(node, selectors.get("image_selector"))
            date_text = self._extract_node_value(node, selectors.get("date_selector"))
            time_text = self._extract_node_value(node, time_selector) if time_selector else None
            start_text = self._combine_date_time_text(date_text, time_text)
            start_at = self._parse_datetime(
                start_text,
                datetime_format=datetime_format,
                locale=locale_hint,
                timezone_name=timezone_name,
            )
            payload = {
                "title": title,
                "url": full_url,
                "description": description,
                "location_text": location_text,
                "venue": venue,
                "image_url": image_url,
                "date_text": date_text,
                "time_text": time_text,
                "start_text": start_text,
            }
            events.append(
                self._build_event_raw(
                    source=source,
                    detected_format="html",
                    title=title,
                    event_url=full_url,
                    start_at=start_at,
                    description=description,
                    location_text=location_text,
                    venue=venue,
                    image_url=image_url,
                    raw_payload=payload,
                )
            )
        return events

    def _parse_rss_events(self, source: EventSource, feed_text: str) -> List[EventRawCreate]:
        parsed = feedparser.parse(feed_text)
        entries = getattr(parsed, "entries", []) or []
        selectors = source.selectors
        item_path = selectors.get("item_path", "entries")
        # For compatibility with json-like path semantics we reuse _resolve_path
        entries_resolved = self._resolve_path({"entries": entries}, item_path)
        if not isinstance(entries_resolved, list):
            entries_resolved = entries
        timezone_name = selectors.get("timezone")
        datetime_format = selectors.get("datetime_format")
        locale_hint = selectors.get("locale")
        events: List[EventRawCreate] = []
        for entry in entries_resolved:
            entry_dict = dict(entry)
            title = self._resolve_path(entry_dict, selectors.get("title_path", "title"))
            if not title:
                continue
            url_value = self._resolve_path(entry_dict, selectors.get("url_path", "link"))
            start_text = self._resolve_path(
                entry_dict,
                selectors.get("start_path", "published") or selectors.get("date"),
            )
            description = self._resolve_path(entry_dict, selectors.get("description_path", "summary"))
            normalized_text = start_text if isinstance(start_text, str) else None
            start_at = self._parse_datetime(
                normalized_text,
                datetime_format=datetime_format,
                locale=locale_hint,
                timezone_name=timezone_name,
            )
            events.append(
                self._build_event_raw(
                    source=source,
                    detected_format="rss",
                    title=str(title),
                    event_url=str(url_value) if url_value else None,
                    start_at=start_at,
                    description=str(description) if description else None,
                    location_text=None,
                    venue=None,
                    image_url=None,
                    raw_payload=entry_dict,
                )
            )
        return events

    def _parse_json_events(self, source: EventSource, payload: Any) -> List[EventRawCreate]:
        selectors = source.selectors
        items_path = selectors["items_path"]
        items = self._resolve_path(payload, items_path)
        if not isinstance(items, list):
            raise ValueError(f"selectors.items_path '{items_path}' did not resolve to a list")
        title_key = selectors.get("title_key", "title")
        url_key = selectors.get("url_key", "url")
        start_key = selectors.get("start_key", "start_at")
        description_key = selectors.get("description_key", "description")
        location_key = selectors.get("location_key", "location")
        venue_key = selectors.get("venue_key", "venue")
        image_key = selectors.get("image_key", "image_url")
        timezone_name = selectors.get("timezone")
        datetime_format = selectors.get("datetime_format")
        locale_hint = selectors.get("locale")

        events: List[EventRawCreate] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = self._get_dict_value(item, title_key)
            if not isinstance(title, str) or not title.strip():
                continue
            url_value = self._get_dict_value(item, url_key)
            start_text = self._get_dict_value(item, start_key)
            description = self._get_dict_value(item, description_key)
            location_text = self._get_dict_value(item, location_key)
            venue = self._get_dict_value(item, venue_key)
            image_url = self._get_dict_value(item, image_key)
            normalized_text = start_text if isinstance(start_text, str) else None
            start_at = self._parse_datetime(
                normalized_text,
                datetime_format=datetime_format,
                locale=locale_hint,
                timezone_name=timezone_name,
            )
            events.append(
                self._build_event_raw(
                    source=source,
                    detected_format="json",
                    title=title.strip(),
                    event_url=str(url_value).strip() if isinstance(url_value, str) else None,
                    start_at=start_at,
                    description=str(description).strip() if isinstance(description, str) else None,
                    location_text=str(location_text).strip() if isinstance(location_text, str) else None,
                    venue=str(venue).strip() if isinstance(venue, str) else None,
                    image_url=str(image_url).strip() if isinstance(image_url, str) else None,
                    raw_payload=item,
                )
            )
        return events

    def _parse_json_ld_events(self, source: EventSource, html_text: str) -> List[EventRawCreate]:
        selectors = source.selectors
        script_selector = selectors.get("script_selector") or DEFAULT_JSON_LD_SCRIPT
        parser = HTMLParser(html_text)
        nodes = parser.css(script_selector)
        if not nodes:
            return []

        items_path = selectors.get("json_items_path")
        type_filter = selectors.get("json_type_filter", "Event")
        title_field = selectors.get("json_title_field", "name")
        url_field = selectors.get("json_url_field", "url")
        start_field = selectors.get("json_start_field", "startDate")
        end_field = selectors.get("json_end_field", "endDate")
        location_field = selectors.get("json_location_field", "location.name")
        image_field = selectors.get("json_image_field", "image")
        description_field = selectors.get("json_description_field", "description")
        timezone_name = selectors.get("timezone")
        datetime_format = selectors.get("datetime_format")
        locale_hint = selectors.get("locale")

        events: List[EventRawCreate] = []

        for node in nodes:
            script_text = (node.text() or "").strip()
            if not script_text:
                continue
            try:
                payload = json.loads(script_text)
            except Exception:
                continue

            resolved_items = self._resolve_path(payload, items_path) if items_path not in (None, "", "$") else payload
            if resolved_items is None:
                resolved_items = payload

            if isinstance(resolved_items, dict):
                iterable = [resolved_items]
            elif isinstance(resolved_items, list):
                iterable = resolved_items
            else:
                continue

            for item in iterable:
                if not isinstance(item, dict):
                    continue
                if not self._json_ld_type_matches(item, type_filter):
                    continue

                title_value = self._resolve_path(item, title_field)
                title = self._stringify_value(title_value)
                if not title:
                    continue

                url_value = self._resolve_path(item, url_field)
                location_value = self._resolve_path(item, location_field)
                description_value = self._resolve_path(item, description_field)
                image_value = self._resolve_path(item, image_field)
                start_value = self._resolve_path(item, start_field)
                end_value = self._resolve_path(item, end_field)

                event_url = self._absolutize_url(
                    source,
                    self._stringify_value(url_value),
                )
                image_url = self._absolutize_url(
                    source,
                    self._stringify_value(image_value),
                )
                start_at = self._parse_datetime(
                    self._stringify_value(start_value),
                    datetime_format=datetime_format,
                    locale=locale_hint,
                    timezone_name=timezone_name,
                )
                end_at = self._parse_datetime(
                    self._stringify_value(end_value),
                    datetime_format=datetime_format,
                    locale=locale_hint,
                    timezone_name=timezone_name,
                )
                events.append(
                    self._build_event_raw(
                        source=source,
                        detected_format="json",
                        title=title,
                        event_url=event_url,
                        start_at=start_at,
                        description=self._stringify_value(description_value),
                        location_text=self._stringify_value(location_value),
                        venue=None,
                        image_url=image_url,
                        raw_payload=item,
                    )
                )
        return events

    def _build_event_raw(
        self,
        *,
        source: EventSource,
        detected_format: str,
        title: str,
        event_url: Optional[str],
        start_at: Optional[datetime],
        description: Optional[str],
        location_text: Optional[str],
        venue: Optional[str],
        image_url: Optional[str],
        raw_payload: Dict[str, Any],
    ) -> EventRawCreate:
        ingest_hash = self._compute_ingest_hash(
            source_id=source.id,
            event_url=event_url,
            start_at=start_at,
            title=title,
        )
        return EventRawCreate(
            event_source_id=source.id,
            title=title,
            description=description,
            location_text=location_text,
            venue=venue,
            event_url=event_url,
            image_url=image_url,
            start_at=start_at,
            end_at=None,
            detected_format=detected_format,  # type: ignore[arg-type]
            ingest_hash=ingest_hash,
            raw_payload=raw_payload,
            processing_state="pending",
        )

    @staticmethod
    def _compute_ingest_hash(
        *,
        source_id: int,
        event_url: Optional[str],
        start_at: Optional[datetime],
        title: Optional[str],
    ) -> str:
        parts = [
            str(source_id),
            (event_url or "").strip().lower(),
            start_at.isoformat() if start_at else "",
            (title or "").strip().lower(),
        ]
        joined = "|".join(parts)
        return hashlib.sha1(joined.encode("utf-8", "ignore")).hexdigest()

    @staticmethod
    def _parse_datetime(
        value: Optional[str],
        *,
        datetime_format: Optional[str] = None,
        locale: Optional[str] = None,
        timezone_name: Optional[str] = None,
    ) -> Optional[datetime]:
        if not value:
            return None
        candidate = value.strip()
        if not candidate:
            return None
        normalized = EventScraperService._normalize_locale_datetime(candidate, locale)
        parsed: Optional[datetime] = None
        if datetime_format:
            translated_format = EventScraperService._translate_datetime_format(datetime_format)
            try:
                parsed = datetime.strptime(normalized, translated_format)
            except Exception:
                parsed = None
        if parsed is None:
            try:
                parsed = date_parser.parse(normalized)
            except Exception:
                return None
        parsed_with_tz = EventScraperService._apply_timezone(parsed, timezone_name)
        return parsed_with_tz.astimezone(timezone.utc)

    @staticmethod
    def _combine_date_time_text(date_text: Optional[str], time_text: Optional[str]) -> Optional[str]:
        parts: List[str] = []
        for value in (date_text, time_text):
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    parts.append(cleaned)
        if not parts:
            return None
        return " ".join(parts)

    @staticmethod
    def _normalize_locale_datetime(value: str, locale: Optional[str]) -> str:
        if not locale or not value:
            return value
        normalized_locale = locale.lower()
        if normalized_locale.startswith("nl"):
            pattern = r"\b(" + "|".join(NL_MONTH_MAP.keys()) + r")\b"

            def replace(match: re.Match[str]) -> str:
                token = match.group(0)
                replacement = NL_MONTH_MAP.get(token.lower())
                if not replacement:
                    return token
                if token.isupper():
                    return replacement.upper()
                if token.istitle():
                    return replacement.capitalize()
                return replacement

            return re.sub(pattern, replace, value, flags=re.IGNORECASE)
        return value

    @staticmethod
    def _translate_datetime_format(fmt: str) -> str:
        translated = fmt
        replacements = [
            ("YYYY", "%Y"),
            ("yyyy", "%Y"),
            ("YY", "%y"),
            ("yy", "%y"),
            ("MMMM", "%B"),
            ("MMM", "%b"),
            ("MM", "%m"),
            ("DD", "%d"),
            ("dd", "%d"),
            ("HH", "%H"),
            ("hh", "%I"),
            ("mm", "%M"),
            ("ss", "%S"),
        ]
        for source, target in replacements:
            translated = translated.replace(source, target)
        return translated

    @staticmethod
    def _apply_timezone(dt: datetime, timezone_name: Optional[str]) -> datetime:
        if dt.tzinfo is not None:
            return dt
        if timezone_name:
            try:
                return dt.replace(tzinfo=ZoneInfo(timezone_name))
            except Exception:
                return dt.replace(tzinfo=timezone.utc)
        return dt.replace(tzinfo=timezone.utc)

    @staticmethod
    def _json_ld_type_matches(item: Dict[str, Any], expected: Optional[str]) -> bool:
        if not expected:
            return True
        expected_lower = expected.lower()
        raw_type = item.get("@type")
        if raw_type is None:
            return False
        if isinstance(raw_type, list):
            return any(str(entry).strip().lower() == expected_lower for entry in raw_type)
        return str(raw_type).strip().lower() == expected_lower

    @staticmethod
    def _stringify_value(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        if isinstance(value, list):
            for entry in value:
                candidate = EventScraperService._stringify_value(entry)
                if candidate:
                    return candidate
            return None
        if isinstance(value, dict):
            if "name" in value:
                return EventScraperService._stringify_value(value["name"])
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @staticmethod
    def _extract_node_value(node: Node, selector: Optional[str]) -> Optional[str]:
        if not selector:
            return None
        target = node
        css = selector
        attr: Optional[str] = None
        if "@" in selector:
            css, attr = selector.split("@", 1)
        css = css.strip()
        if css:
            target = node.css_first(css)
            if target is None:
                return None
        if attr:
            attr = attr.strip()
            if attr == "text":
                return target.text().strip()
            return target.attributes.get(attr)
        return target.text().strip()

    @staticmethod
    def _absolutize_url(source: EventSource, url_value: Optional[str]) -> Optional[str]:
        if not url_value:
            return None
        if url_value.startswith(("http://", "https://")):
            return url_value
        base = source.list_url or source.base_url
        return urljoin(base, url_value)

    @staticmethod
    def _split_path(path: str) -> List[str]:
        cleaned = path.strip()
        if cleaned.startswith("$."):
            cleaned = cleaned[2:]
        cleaned = cleaned.strip(".")
        return [segment for segment in cleaned.split(".") if segment]

    def _resolve_path(self, payload: Any, path: Optional[str]) -> Any:
        if payload is None or not path:
            return payload
        current = payload
        for chunk in self._split_path(path):
            if isinstance(current, dict):
                current = current.get(chunk)
            elif isinstance(current, list):
                try:
                    idx = int(chunk)
                except ValueError:
                    return None
                if idx < 0 or idx >= len(current):
                    return None
                current = current[idx]
            else:
                return None
        return current

    @staticmethod
    def _get_dict_value(item: Dict[str, Any], key: Optional[str]) -> Any:
        if not key:
            return None
        return item.get(key)


async def scrape_sources(sources: Sequence[EventSource]) -> List[EventScraperResult]:
    if not sources:
        return []
    async with EventScraperService() as service:
        results = await asyncio.gather(*(service.scrape_source(source) for source in sources))
    return list(results)


