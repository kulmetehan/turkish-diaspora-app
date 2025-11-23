#!/usr/bin/env python3
"""
news_sources_check.py

Lightweight CLI to ensure configs/news_sources.yml can be parsed by workers.
Logs totals per category and exits with code 0 even if the config is empty,
while invalid entries are already reported by the loader.
"""

from __future__ import annotations

from collections import Counter
import sys
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parent
BACKEND_DIR = SCRIPTS_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.models.news_sources import (  # noqa: E402
    clear_news_sources_cache,
    get_all_news_sources,
)


def main() -> int:
    configure_logging(service_name="worker")
    logger = get_logger()

    clear_news_sources_cache()
    sources = get_all_news_sources()

    if not sources:
        logger.warning("news_sources_check_no_sources_loaded")
        return 0

    counts = Counter(source.category for source in sources)
    logger.info(
        "news_sources_check_ok",
        total=len(sources),
        per_category=dict(counts),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


