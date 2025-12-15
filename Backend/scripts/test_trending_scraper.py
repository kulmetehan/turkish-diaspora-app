#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test X Trending Topics Scraper
- Tests if scraper works or if X has anti-scraping
- Shows which strategy works (if any)
- Provides detailed error information
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add Backend to path for imports
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from services.news_trending_x_scraper import fetch_trending_topics_scraper


async def main():
    """Test the scraper."""
    print("=" * 80)
    print("Testing X Trending Topics Scraper")
    print("=" * 80)
    print()
    
    print("Attempting to scrape trending topics for Netherlands (nl)...")
    print("-" * 80)
    print()
    
    try:
        result = await fetch_trending_topics_scraper(limit=10, country="nl")
        
        print(f"Result:")
        print(f"  Topics found: {len(result.topics)}")
        print(f"  Unavailable reason: {result.unavailable_reason}")
        print()
        
        if result.topics:
            print("✅ SUCCESS: Scraper is working!")
            print()
            print("Trending topics found:")
            print("-" * 80)
            for i, topic in enumerate(result.topics, 1):
                print(f"{i}. {topic.title}")
                print(f"   URL: {topic.url}")
                print()
            print("=" * 80)
            print("✅ Test PASSED: Scraper successfully retrieved trending topics")
            return 0
        else:
            print("❌ FAILED: No topics found")
            print()
            if result.unavailable_reason:
                print(f"Reason: {result.unavailable_reason}")
                print()
                print("Possible causes:")
                if "blocked" in result.unavailable_reason:
                    print("  - X is blocking the scraper (anti-scraping detected)")
                    print("  - May need authentication (cookies/tokens)")
                    print("  - X may require browser automation instead of simple HTTP requests")
                elif "rate_limited" in result.unavailable_reason:
                    print("  - X is rate limiting requests")
                    print("  - Wait a few minutes and try again")
                elif "error" in result.unavailable_reason:
                    print("  - Error occurred during scraping")
                    print("  - Check backend logs for detailed error information")
                elif "http_" in result.unavailable_reason:
                    status_code = result.unavailable_reason.split("_")[-1]
                    print(f"  - HTTP {status_code} error")
                    print("  - X may have changed their API structure")
            print()
            print("💡 Next steps:")
            print("  - Check backend logs for detailed strategy attempts")
            print("  - Consider using browser automation (Selenium/Playwright)")
            print("  - Consider using third-party APIs (Trendstools, Apify, TrendsonX)")
            print()
            print("=" * 80)
            print("❌ Test FAILED: Scraper could not retrieve trending topics")
            return 1
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print()
        import traceback
        traceback.print_exc()
        print()
        print("=" * 80)
        print("❌ Test FAILED: Exception occurred")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
