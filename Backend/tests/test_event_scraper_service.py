from __future__ import annotations

from datetime import datetime, timezone

from app.models.event_sources import EventSource
from services.event_scraper_service import EventScraperService


def _make_event_source(**overrides):
    base = {
        "id": 1,
        "key": "test_source",
        "name": "Test Source",
        "base_url": "https://example.com",
        "list_url": "https://example.com/events",
        "selectors": {
            "format": "html",
            "item_selector": ".event",
            "title_selector": ".event-title",
            "url_selector": ".event-title@href",
        },
        "interval_minutes": 60,
        "status": "active",
        "last_run_at": None,
        "last_success_at": None,
        "last_error_at": None,
        "last_error": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return EventSource(**base)


def test_parse_html_events_basic() -> None:
    service = EventScraperService()
    html = """
    <div class="event">
        <a class="event-title" href="/concerts/awesome">Awesome Concert</a>
        <time class="event-date">2025-12-01T18:00:00Z</time>
    </div>
    """
    source = _make_event_source(
        selectors={
            "format": "html",
            "item_selector": ".event",
            "title_selector": ".event-title",
            "url_selector": ".event-title@href",
            "date_selector": ".event-date",
        }
    )

    events = service._parse_html_events(source, html)

    assert len(events) == 1
    event = events[0]
    assert event.title == "Awesome Concert"
    assert event.event_url == "https://example.com/concerts/awesome"
    assert event.start_at.isoformat() == "2025-12-01T18:00:00+00:00"
    assert len(event.ingest_hash) == 40


def test_parse_json_events_with_items_path() -> None:
    service = EventScraperService()
    source = _make_event_source(
        selectors={
            "format": "json",
            "items_path": "data.items",
            "title_key": "name",
            "url_key": "url",
            "start_key": "start",
        }
    )
    payload = {
        "data": {
            "items": [
                {
                    "name": "Community Meetup",
                    "url": "https://example.com/events/meetup",
                    "start": "2025-11-12T19:30:00+01:00",
                }
            ]
        }
    }

    events = service._parse_json_events(source, payload)

    assert len(events) == 1
    event = events[0]
    assert event.title == "Community Meetup"
    assert event.event_url == "https://example.com/events/meetup"
    assert event.start_at.isoformat() == "2025-11-12T18:30:00+00:00"


def test_parse_rss_events_defaults() -> None:
    service = EventScraperService()
    source = _make_event_source(
        selectors={
            "format": "rss",
            "item_path": "entries",
            "title_path": "title",
            "url_path": "link",
        }
    )
    feed = """
    <rss>
        <channel>
            <item>
                <title>Festival</title>
                <link>https://example.com/festival</link>
                <pubDate>Wed, 19 Nov 2025 20:00:00 GMT</pubDate>
            </item>
        </channel>
    </rss>
    """

    events = service._parse_rss_events(source, feed)

    assert len(events) == 1
    event = events[0]
    assert event.title == "Festival"
    assert event.event_url == "https://example.com/festival"
    # start_at may be None (feed parser may not parse pubDate), but ingest hash must exist
    assert len(event.ingest_hash) == 40


def test_parse_html_events_with_locale_and_timezone() -> None:
    service = EventScraperService()
    html = """
    <div class="event">
        <div class="event-date">12 januari 2025</div>
        <div class="event-time">20:00</div>
        <a class="event-title" href="/nieuwjaar">Nieuwjaar</a>
    </div>
    """
    source = _make_event_source(
        selectors={
            "format": "html",
            "item_selector": ".event",
            "title_selector": ".event-title",
            "url_selector": ".event-title@href",
            "date_selector": ".event-date",
            "time_selector": ".event-time",
            "datetime_format": "DD MMMM YYYY HH:mm",
            "locale": "nl_NL",
            "timezone": "Europe/Amsterdam",
        }
    )

    events = service._parse_html_events(source, html)

    assert len(events) == 1
    event = events[0]
    assert event.title == "Nieuwjaar"
    assert event.start_at.isoformat() == "2025-01-12T19:00:00+00:00"


def test_parse_json_ld_events_ahoy() -> None:
    service = EventScraperService()
    html = """
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@graph": [
        {
          "@type": "Event",
          "name": "LD Event",
          "url": "https://example.com/ld",
          "startDate": "2025-06-01T20:00:00+02:00",
          "location": {"name": "Rotterdam"},
          "description": "Json-LD powered event",
          "image": "https://example.com/image.jpg"
        }
      ]
    }
    </script>
    """
    source = _make_event_source(
        selectors={
            "format": "json_ld",
            "json_items_path": "$.@graph",
            "json_type_filter": "Event",
            "json_title_field": "name",
            "json_url_field": "url",
            "json_start_field": "startDate",
            "json_location_field": "location.name",
            "json_description_field": "description",
            "json_image_field": "image",
            "timezone": "Europe/Amsterdam",
        }
    )

    events = service._parse_json_ld_events(source, html)

    assert len(events) == 1
    event = events[0]
    assert event.title == "LD Event"
    assert event.event_url == "https://example.com/ld"
    assert event.location_text == "Rotterdam"
    assert event.start_at.isoformat() == "2025-06-01T18:00:00+00:00"
    assert event.description == "Json-LD powered event"


