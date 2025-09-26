#!/usr/bin/env python3
"""
Google News RSS Aggregator for Turkish Diaspora App

Fixes in deze versie:
- Headers worden opgeschoond: nooit None-waarden naar httpx (verhelpt TypeError).
- Google News redirect resolver is uitgeschakeld om EU consent-loops te vermijden.
- Publicatiedata worden naar naive UTC genormaliseerd (verhelpt aware/naive subtract error).
- ETag wordt alleen gezet/gelezen als er daadwerkelijk een string-waarde is.
- Geen directe DB-writes (runner post zelf naar 'items').

Deze module levert een NewsAggregator-klasse die door ingest/news_ingestion_system.py
wordt gebruikt.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, urlparse

import feedparser
import httpx

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("news")

# Minder spam van httpx
logging.getLogger("httpx").setLevel(logging.WARNING)


# ---------- Data Model ----------
@dataclass
class NewsItem:
    id: str
    source: str
    language: str
    title: str
    summary: str
    url: str
    image_url: Optional[str]
    published_at: str  # ISO8601 UTC (ending with Z)
    category: Optional[str]
    score: float
    original_data: Dict


# ---------- Helpers ----------
def is_google_news_link(url: str) -> bool:
    return bool(url) and ("news.google.com" in url or "consent.google.com" in url)


def resolve_google_news_link(url: str) -> str:
    """
    Resolving is bewust uitgeschakeld ivm EU consent interstitials.
    We geven de originele Google News-link terug; runner/FE kan die gewoon openen.
    """
    if not is_google_news_link(url):
        return url
    logger.debug(f"[resolve_google_news_link] Skipping resolution for: {url}")
    return url


# ---------- Aggregator ----------
class NewsAggregator:
    def __init__(self, config_path: str = "news_config.json"):
        self.config = self._load_config(config_path)
        self.client = httpx.Client(
            timeout=httpx.Timeout(connect=5.0, read=5.0, write=5.0, pool=5.0)
        )
        # Cache structuur
        self.cache: Dict[str, Dict] = {
            "nl": {"items": [], "last_fetch": None, "etag": None},
            "tr": {"items": [], "last_fetch": None, "etag": None},
            "merged": {"items": [], "last_update": None},
        }

    # -------------------- Config --------------------
    def _load_config(self, config_path: str) -> Dict:
        if Path(config_path).exists():
            try:
                return json.loads(Path(config_path).read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"[config] failed to load {config_path}: {e}")
        # fallback defaults (minimal)
        return {
            "sources": {
                "nl": {
                    "outlets": ["ad.nl", "nu.nl", "nos.nl", "rtlnieuws.nl"],
                    "default_topics": ["Nederland"],
                    "diaspora_topics": ["Turkije", "Turkse gemeenschap"],
                },
                "tr": {
                    "outlets": ["hurriyet.com.tr", "aa.com.tr", "milliyet.com.tr"],
                    "default_topics": ["Türkiye"],
                    "diaspora_topics": ["Hollanda", "Avrupa", "gurbetçi"],
                },
            },
            "ranking": {
                "freshness_weight": 0.4,
                "source_weight": 0.3,
                "engagement_weight": 0.2,
                "relevance_weight": 0.1,
                "dedupe_penalty": 0.5,
            },
            "cache": {"ttl_hours": 2, "max_items": 1000, "poll_interval_minutes": 15},
            "api": {"default_limit": 50, "max_limit": 200},
        }

    # -------------------- URL building --------------------
    def build_google_news_url(
        self, lang: str, query_type: str = "general", topic: Optional[str] = None
    ) -> str:
        base_url = "https://news.google.com/rss/search"
        if lang == "nl":
            hl, gl, ceid = "nl", "NL", "NL:nl"
            outlets = self.config["sources"]["nl"]["outlets"]
        elif lang == "tr":
            hl, gl, ceid = "tr", "TR", "TR:tr"
            outlets = self.config["sources"]["tr"]["outlets"]
        else:
            raise ValueError(f"Unsupported language: {lang}")

        if query_type == "general":
            site_queries = [f"site:{o}" for o in outlets]
            query = " OR ".join(site_queries)
        elif query_type == "topic" and topic:
            query = topic
        elif query_type == "diaspora":
            topics = self.config["sources"][lang]["diaspora_topics"]
            query = " OR ".join([f'"{t}"' for t in topics])
        else:
            query = ""

        params = f"q={quote(query)}&hl={hl}&gl={gl}&ceid={ceid}"
        return f"{base_url}?{params}"

    # -------------------- Fetching --------------------
    def fetch_feed(self, url: str, etag: Optional[str] = None) -> Tuple[List[Dict], Optional[str]]:
        """
        Fetch RSS met real User-Agent en defensieve timeouts.
        Retourneert [] bij fout en geeft (entries, etag).
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
        }
        if etag:
            headers["If-None-Match"] = str(etag)

        # Opschonen: geen None/lege values naar httpx
        headers = {k: v for k, v in headers.items() if isinstance(v, (str, bytes)) and v}

        try:
            r = self.client.get(url, headers=headers, follow_redirects=True)
        except httpx.TimeoutException:
            logger.warning(f"[fetch_feed] TIMEOUT -> {url}")
            return [], etag
        except Exception as ex:
            logger.error(f"[fetch_feed] ERROR {ex} -> {url}")
            return [], etag

        if r.status_code == 304:
            logger.info(f"[fetch_feed] 304 Not Modified -> {url}")
            return [], etag
        if r.status_code != 200:
            logger.warning(f"[fetch_feed] HTTP {r.status_code} -> {url}")
            return [], etag

        # ETag uit response, indien aanwezig
        new_etag = r.headers.get("ETag") or etag

        feed = feedparser.parse(r.text)
        entries = []
        for e in feed.entries:
            source_title = ""
            try:
                source_obj = getattr(e, "source", None)
                if source_obj and hasattr(source_obj, "title"):
                    source_title = source_obj.title
            except Exception:
                pass

            entries.append(
                {
                    "title": e.get("title", ""),
                    "link": e.get("link", ""),
                    "description": e.get("description", "") or e.get("summary", ""),
                    "published": e.get("published", "") or e.get("updated", ""),
                    "raw": e,
                    "source": source_title,
                }
            )

        logger.info(f"[fetch_feed] OK {len(entries)} entries <- {url}")
        return entries, new_etag

    # -------------------- Text/Language helpers --------------------
    def detect_language(self, item: Dict, feed_lang: str) -> str:
        text = f"{item.get('title','')} {item.get('description','')}".lower()
        tr_words = [" ve ", " bir ", " için ", " ile ", " bu ", " da ", " olan "]
        nl_words = [" de ", " het ", " een ", " van ", " en ", " in ", " op ", " met "]
        tr_count = sum(w in text for w in tr_words)
        nl_count = sum(w in text for w in nl_words)
        if tr_count > nl_count * 1.5:
            return "tr"
        if nl_count > tr_count * 1.5:
            return "nl"
        return feed_lang

    def extract_image_url(self, item: Dict) -> Optional[str]:
        raw = item.get("raw", {})
        try:
            media = raw.get("media_content", [])
            if media and isinstance(media, list) and "url" in media[0]:
                return media[0]["url"]
        except Exception:
            pass
        try:
            thumbs = raw.get("media_thumbnail", [])
            if thumbs and isinstance(thumbs, list) and "url" in thumbs[0]:
                return thumbs[0]["url"]
        except Exception:
            pass
        desc = item.get("description", "")
        m = re.search(r'<img[^>]+src="([^"]+)"', desc)
        return m.group(1) if m else None

    def clean_text(self, html: str) -> str:
        text = re.sub(r"<[^>]+>", "", html or "")
        text = " ".join(text.split())
        text = re.sub(r"\s-\s[^-]+$", "", text)  # "title - Source"
        return text.strip()

    def generate_item_id(self, item: Dict) -> str:
        key = f"{item.get('link','')}{item.get('title','')}".encode("utf-8")
        return hashlib.md5(key).hexdigest()

    def normalize_url(self, url: str) -> str:
        p = urlparse(url.lower())
        domain = p.netloc.replace("www.", "")
        path = p.path.rstrip("/")
        return f"{domain}{path}"

    def calculate_similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, self.clean_text(a).lower(), self.clean_text(b).lower()).ratio()

    def parse_pubdate(self, published_str: str, raw_item: Dict) -> datetime:
        """
        Retourneert een naive UTC datetime (zonder tzinfo) om aware/naive errors te voorkomen.
        """
        # 1) Probeer feedparser-struct_time
        try:
            pp = raw_item.get("raw", {}).get("published_parsed") or raw_item.get("raw", {}).get("updated_parsed")
            if pp:
                dt = datetime(pp.tm_year, pp.tm_mon, pp.tm_mday, pp.tm_hour, pp.tm_min, pp.tm_sec)
                return dt  # struct_time is al naive
        except Exception:
            pass

        # 2) Probeer email.utils parser
        try:
            dt = parsedate_to_datetime(published_str)
            if dt is None:
                raise ValueError("parsedate_to_datetime returned None")
            # Normaliseer naar naive UTC
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except Exception:
            # 3) Fallback: nu (naive)
            return datetime.utcnow()

    # -------------------- Scoring & Dedup --------------------
    def calculate_score(self, raw_item: Dict, lang: str) -> float:
        w = self.config["ranking"]
        score = 0.0

        pub_dt = self.parse_pubdate(raw_item.get("published", ""), raw_item)
        age_h = (datetime.utcnow() - pub_dt).total_seconds() / 3600.0
        freshness = max(0.0, 1.0 - (age_h / 24.0))
        score += freshness * w["freshness_weight"]

        source_text = (raw_item.get("source") or "").lower()
        outlets = [o.lower() for o in self.config["sources"][lang]["outlets"]]
        score += w["source_weight"] if any(o in source_text for o in outlets) else 0.5 * w["source_weight"]

        text = f"{raw_item.get('title','')} {raw_item.get('description','')}".lower()
        topics = [t.lower() for t in self.config["sources"][lang]["diaspora_topics"]]
        rel = sum(1 for t in topics if t in text) / (len(topics) or 1)
        score += rel * w["relevance_weight"]

        score += 0.5 * w["engagement_weight"]
        return min(1.0, score)

    def deduplicate_items(self, items: List[NewsItem]) -> List[NewsItem]:
        seen_urls = set()
        seen_titles: List[str] = []
        out: List[NewsItem] = []
        for it in items:
            nu = self.normalize_url(it.url)
            if nu in seen_urls:
                it.score *= self.config["ranking"]["dedupe_penalty"]
                continue
            dup = any(self.calculate_similarity(it.title, t) > 0.86 for t in seen_titles)
            if dup:
                it.score *= self.config["ranking"]["dedupe_penalty"]
                continue
            seen_urls.add(nu)
            seen_titles.append(it.title)
            out.append(it)
        return out

    # -------------------- Normalize --------------------
    def normalize_item(self, raw_item: Dict, feed_lang: str) -> NewsItem:
        detected_lang = self.detect_language(raw_item, feed_lang)
        title = self.clean_text(raw_item.get("title", ""))
        summary = self.clean_text(raw_item.get("description", ""))[:500]

        source_txt = raw_item.get("source") or ""
        if not source_txt:
            url0 = raw_item.get("link", "")
            source_txt = urlparse(url0).netloc.replace("www.", "")

        pub_dt = self.parse_pubdate(raw_item.get("published", ""), raw_item)
        published_at = pub_dt.isoformat() + "Z"  # we houden naive -> suffix Z

        # Geen redirect-resolution (EU consent-loop vermijden)
        url_raw = raw_item.get("link") or raw_item.get("url") or ""
        resolved_url = resolve_google_news_link(url_raw)

        return NewsItem(
            id=self.generate_item_id(raw_item),
            source=source_txt,
            language=detected_lang,
            title=title,
            summary=summary,
            url=resolved_url,
            image_url=self.extract_image_url(raw_item),
            published_at=published_at,
            category=None,
            score=self.calculate_score(raw_item, feed_lang),
            original_data=raw_item,
        )

    def to_item(self, raw_item: Dict, feed_lang: str) -> NewsItem:
        """
        Wrapper zodat we optioneel een boost kunnen meegeven via raw_item.get("__boost").
        """
        item = self.normalize_item(raw_item, feed_lang)
        boost = raw_item.get("__boost")
        if isinstance(boost, (int, float)) and boost > 0:
            item.score *= float(boost)
        return item

    # -------------------- Fetch per language --------------------
    def fetch_language_raw(self, lang: str) -> List[Dict]:
        """
        Haalt 'general' + 'diaspora' feeds voor een taal op en voegt samen.
        Diaspora-items krijgen een lichte score-boost via __boost.
        """
        entries: List[Dict] = []

        # General
        general_url = self.build_google_news_url(lang, "general")
        cache_entry = self.cache.get(lang, {})
        etag_val = cache_entry.get("etag")
        general_entries, new_etag = self.fetch_feed(general_url, etag_val)
        if new_etag and lang in self.cache:
            self.cache[lang]["etag"] = new_etag
        entries.extend(general_entries)

        # Diaspora (geen etag-caching nodig)
        diaspora_url = self.build_google_news_url(lang, "diaspora")
        diaspora_entries, _ = self.fetch_feed(diaspora_url, None)
        # markeer een boost
        for e in diaspora_entries:
            e["__boost"] = 1.2
        entries.extend(diaspora_entries)

        return entries

    def fetch_language_feed(self, lang: str, force_refresh: bool = False) -> List[NewsItem]:
        cache = self.cache[lang]
        if not force_refresh and cache["last_fetch"]:
            age_min = (datetime.utcnow() - cache["last_fetch"]).total_seconds() / 60.0
            if age_min < self.config["cache"]["poll_interval_minutes"]:
                logger.info(f"[fetch_language_feed] {lang} using cache ({len(cache['items'])} items)")
                return cache["items"]

        all_raw = self.fetch_language_raw(lang)
        items: List[NewsItem] = [self.to_item(r, lang) for r in all_raw]

        logger.info(f"[fetch_language_feed] {lang} TOTAL normalized: {len(items)}")
        self.cache[lang]["items"] = items
        self.cache[lang]["last_fetch"] = datetime.utcnow()
        return items

    # -------------------- Merge & API helpers --------------------
    def merge_and_rank(self, nl: List[NewsItem], tr: List[NewsItem]) -> List[NewsItem]:
        items = nl + tr
        items = self.deduplicate_items(items)
        items.sort(key=lambda x: x.score, reverse=True)
        return items[: self.config["cache"]["max_items"]]

    def get_feed(
        self,
        lang: str = "all",
        limit: int = 50,
        offset: int = 0,
        topic: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Dict:
        if lang in ("all", "nl,tr"):
            nl = self.fetch_language_feed("nl", force_refresh)
            tr = self.fetch_language_feed("tr", force_refresh)
            items = self.merge_and_rank(nl, tr)
        elif lang in ("nl", "tr"):
            items = self.fetch_language_feed(lang, force_refresh)
        else:
            items = []

        if topic:
            t = topic.lower()
            items = [i for i in items if t in i.title.lower() or t in (i.summary or "").lower()]

        page = items[offset : offset + limit]
        return {
            "items": [asdict(i) for i in page],
            "total": len(items),
            "limit": limit,
            "offset": offset,
            "language": lang,
            "topic": topic,
            "last_update": datetime.utcnow().isoformat() + "Z",
        }

    def refresh_all(self) -> Dict:
        nl = self.fetch_language_feed("nl", force_refresh=True)
        tr = self.fetch_language_feed("tr", force_refresh=True)
        merged = self.merge_and_rank(nl, tr)

        self.cache["merged"]["items"] = merged
        self.cache["merged"]["last_update"] = datetime.utcnow()
        return {
            "status": "success",
            "nl_items": len(nl),
            "tr_items": len(tr),
            "merged_items": len(merged),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def __del__(self):
        try:
            self.client.close()
        except Exception:
            pass


if __name__ == "__main__":
    aggr = NewsAggregator()
    print("Refreshing all feeds (no DB writes from this file)...")
    res = aggr.refresh_all()
    print(json.dumps(res, indent=2))
    test = aggr.get_feed(lang="all", limit=5)
    for it in test["items"]:
        flag = "🇳🇱" if it["language"] == "nl" else "🇹🇷"
        print(f"{flag} {it['title']} [{it['source']}] -> {it['url']}")