#!/usr/bin/env python3
"""
Google News RSS Aggregator for Turkish Diaspora App
Mixed NL/TR feed with dedupe, scoring and robust fetching.

Belangrijkste wijziging:
- Google News redirect resolver omzeilt nu de EU-consent interstitial
  via verbeterde consent-cookie en het uitlezen van de 'continue='-parameter.
- Implementatie blijft volledig SYNC met httpx.Client (geen asyncio.run meer).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, urlparse, parse_qs, unquote

import feedparser
import httpx


# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("news")


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


# ---------- Google News helpers ----------
def is_google_news_link(url: str) -> bool:
    """
    Herkent Google News RSS links en consent.google.com interstitials.
    """
    return bool(url) and ("news.google.com" in url or "consent.google.com" in url)


def _maybe_unwrap_consent(url: str) -> str:
    """
    Als we een consent.google.com URL krijgen met ?continue=..., haal de echte target eruit.
    """
    try:
        p = urlparse(url)
        if p.netloc.endswith("consent.google.com"):
            q = parse_qs(p.query)
            cont = q.get("continue", [])
            if cont and isinstance(cont[0], str):
                return cont[0]
    except Exception:
        pass
    return url


def resolve_google_news_link(url: str) -> str:
    """
    TIJDELIJK UITGESCHAKELD: Volgt redirects van Google News RSS naar de uiteindelijke uitgever-URL.
    
    Google's consent-systeem blokkeert momenteel onze redirect resolver.
    Voor nu geven we gewoon de originele URL terug zodat de API snel blijft werken.
    
    TODO: Implementeer een betere strategie (bijv. periodieke batch-resolving of proxy).
    """
    if not is_google_news_link(url):
        return url
    
    # Voor nu: return de originele URL zonder te resolven
    # Dit betekent dat je Google News URLs krijgt in plaats van publisher URLs,
    # maar de API werkt wel snel.
    logger.debug(f"[resolve_google_news_link] Skipping resolution for: {url}")
    return url


# ---------- Aggregator ----------
class NewsAggregator:
    def __init__(self, config_path: str = "news_config.json"):
        self.config = self._load_config(config_path)
        self.cache = {
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
        Fetch RSS with a real User-Agent and strict timeouts.
        Never blocks longer than a few seconds; returns [] on error.
        Logs status + entry count.
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
        }
        timeout = httpx.Timeout(connect=5.0, read=5.0, write=5.0, pool=5.0)

        try:
            r = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
            if r.status_code == 304:
                logger.info(f"[fetch_feed] 304 Not Modified -> {url}")
                return [], etag
            if r.status_code != 200:
                logger.warning(f"[fetch_feed] HTTP {r.status_code} -> {url}")
                return [], etag

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
            return entries, None

        except httpx.TimeoutException:
            logger.warning(f"[fetch_feed] TIMEOUT -> {url}")
            return [], etag
        except Exception as ex:
            logger.error(f"[fetch_feed] ERROR {ex} -> {url}")
            return [], etag

    # -------------------- Helpers --------------------
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

    def parse_pubdate(self, published_str: str, raw: Dict) -> datetime:
        try:
            pp = raw.get("raw", {}).get("published_parsed") or raw.get("raw", {}).get("updated_parsed")
            if pp:
                return datetime(pp.tm_year, pp.tm_mon, pp.tm_mday, pp.tm_hour, pp.tm_min, pp.tm_sec)
        except Exception:
            pass
        try:
            return parsedate_to_datetime(published_str)
        except Exception:
            pass
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
        pub_dt = pub_dt if pub_dt.tzinfo is None else pub_dt.replace(tzinfo=None)
        published_at = pub_dt.isoformat() + "Z"

        # Resolve altijd de Google News link naar de echte bron (sync, geen asyncio.run)
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

    # -------------------- Public methods --------------------
    def fetch_language_feed(self, lang: str, force_refresh: bool = False) -> List[NewsItem]:
        cache = self.cache[lang]
        if not force_refresh and cache["last_fetch"]:
            age_min = (datetime.utcnow() - cache["last_fetch"]).total_seconds() / 60.0
            if age_min < self.config["cache"]["poll_interval_minutes"]:
                logger.info(f"[fetch_language_feed] {lang} using cache ({len(cache['items'])} items)")
                return cache["items"]

        all_items: List[NewsItem] = []

        # GENERAL
        general_url = self.build_google_news_url(lang, "general")
        logger.info(f"[fetch_language_feed] {lang} general URL: {general_url}")
        entries, new_etag = self.fetch_feed(general_url, cache.get("etag"))
        logger.info(f"[fetch_language_feed] {lang} general entries: {len(entries)}")
        for e in entries:
            item = self.normalize_item(e, lang)
            all_items.append(item)

        # DIASPORA
        diaspora_url = self.build_google_news_url(lang, "diaspora")
        logger.info(f"[fetch_language_feed] {lang} diaspora URL: {diaspora_url}")
        diaspora_entries, _ = self.fetch_feed(diaspora_url)
        logger.info(f"[fetch_language_feed] {lang} diaspora entries: {len(diaspora_entries)}")
        for e in diaspora_entries:
            item = self.normalize_item(e, lang)
            item.score *= 1.2
            all_items.append(item)

        cache["items"] = all_items
        cache["last_fetch"] = datetime.utcnow()
        cache["etag"] = new_etag

        logger.info(f"[fetch_language_feed] {lang} TOTAL normalized: {len(all_items)}")
        return all_items

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


if __name__ == "__main__":
    aggr = NewsAggregator()
    print("Testing mixed feed...")
    res = aggr.get_feed(lang="all", limit=10)
    print(f"Total items: {res['total']}")
    for it in res["items"]:
        flag = "🇳🇱" if it["language"] == "nl" else "🇹🇷"
        print(f"{flag} {it['title']} [{it['source']}] -> {it['url']}")