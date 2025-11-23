from __future__ import annotations

import json
from pathlib import Path

from services.news_location_tagging import (
    TAG_LOCAL,
    TAG_NONE,
    TAG_ORIGIN,
    derive_location_tag,
)

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "news_location_samples.json").read_text(encoding="utf-8")
)


def test_ai_mentions_drive_local_tag():
    article = FIXTURES["local"]
    tag, context = derive_location_tag(
        title=article["title"],
        summary=article["summary"],
        content=article["content"],
        ai_mentions=[{"city_key": "rotterdam", "country": "nl", "confidence": 0.92}],
    )
    assert tag == TAG_LOCAL
    assert context["matches"][0]["source"] == "ai"
    assert context["matches"][0]["city_key"] == "rotterdam"


def test_text_detection_covers_origin_city():
    article = FIXTURES["origin"]
    tag, context = derive_location_tag(
        title=article["title"],
        summary=article["summary"],
        content=article["content"],
        ai_mentions=[],
    )
    assert tag == TAG_ORIGIN
    assert any(match["source"] == "text" for match in context["matches"])


def test_conflicting_countries_fall_back_to_none():
    article = FIXTURES["local"]
    tag, _ = derive_location_tag(
        title=article["title"],
        summary=article["summary"],
        content=article["content"],
        ai_mentions=[
            {"city_key": "rotterdam", "country": "nl", "confidence": 0.9},
            {"city_key": "ankara", "country": "tr", "confidence": 0.9},
        ],
    )
    assert tag == TAG_NONE


