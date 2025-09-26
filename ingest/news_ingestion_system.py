# ingest/news_ingestion_system.py
"""
Runner die:
1) NewsAggregator draait (NL + TR)
2) items merge & rank
3) mapt naar DB-rijen
4) schrijft in Supabase 'items' met ignore-duplicates op url

Uitvoeren vanaf projectroot (met venv actief):
    python -m ingest.news_ingestion_system
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from dotenv import load_dotenv, find_dotenv

# Laad .env betrouwbaar, ook als je niet in root staat
load_dotenv(find_dotenv(usecwd=True))

# Onze ingest helper (PostgREST + on_conflict=url)
from ingest.supabase_ingest import ingest_aggregated_items

# Jouw aggregator-klasse
from ingest.google_news_aggregator import NewsAggregator

logger = logging.getLogger("pipeline")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _ch = logging.StreamHandler()
    _ch.setLevel(logging.INFO)
    logger.addHandler(_ch)


def _newsitem_to_row_dict(it: Dict[str, Any]) -> Dict[str, Any]:
    """
    Zet NewsItem (asdict) om naar het schema van 'items'.
    Verplichte velden: kind, title, url, published_at, lang
    Optioneel: summary_tr/summary_nl, tags, regions, quality_score, source_id
    """
    # published_at van aggregator eindigt op 'Z'; supabase_ingest normaliseert dat prima.
    lang = it.get("language") or it.get("lang") or "nl"
    row: Dict[str, Any] = {
        "kind": "news",
        "title": it.get("title", ""),
        "url": it.get("url", ""),
        "published_at": it.get("published_at"),
        "lang": lang,
        "quality_score": float(it.get("score", 0.5)),
        # optioneel:
        "tags": [],
        "regions": [],
    }
    summary = it.get("summary") or ""
    if lang == "nl":
        row["summary_nl"] = summary[:500]
    elif lang == "tr":
        row["summary_tr"] = summary[:500]
    else:
        # niks doen; veld is optioneel
        pass
    return row


def main() -> None:
    # 1) Aggregator draaien (force_refresh=True voor expliciet ophalen)
    agg = NewsAggregator()
    nl_items = agg.fetch_language_feed("nl", force_refresh=True)
    tr_items = agg.fetch_language_feed("tr", force_refresh=True)

    # 2) Merge & rank
    merged = agg.merge_and_rank(nl_items, tr_items)
    logger.info("Merged set: %d items", len(merged))

    # 3) Map naar dicts voor DB
    # NewsItem is een dataclass; in get_feed() gebruikte je asdict(i). Hier werken we met objecten.
    merged_dicts: List[Dict[str, Any]] = []
    for obj in merged:
        # obj heeft attributes van dataclass NewsItem
        item_dict = {
            "id": getattr(obj, "id", ""),
            "source": getattr(obj, "source", ""),
            "language": getattr(obj, "language", ""),
            "title": getattr(obj, "title", ""),
            "summary": getattr(obj, "summary", ""),
            "url": getattr(obj, "url", ""),
            "image_url": getattr(obj, "image_url", None),
            "published_at": getattr(obj, "published_at", None),
            "category": getattr(obj, "category", None),
            "score": getattr(obj, "score", 0.5),
        }
        merged_dicts.append(item_dict)

    # 4) Map naar DB-rijen
    rows = [_newsitem_to_row_dict(it) for it in merged_dicts]

    # 5) Wegschrijven (duplicates op url genegeerd)
    res = ingest_aggregated_items(rows, default_kind="news", default_source_id=None)
    logger.info("Ingest klaar. Pogingen: %(attempted)s | Nieuwe (schatting): %(inserted_estimate)s", res)


if __name__ == "__main__":
    main()
