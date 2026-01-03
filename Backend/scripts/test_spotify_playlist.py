#!/usr/bin/env python3
"""
Test script to verify Spotify playlist HTML scraping with Playwright.
Run this to debug playlist scraping issues.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add Backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv
    env_path = BACKEND_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except Exception:
    pass  # Environment variables might already be set

from services.news_trending_spotify_scraper import fetch_spotify_tracks_scraper, SpotifyResult

PLAYLISTS = {
    "nl": "37i9dQZEVXbMQaPQjt027d",
    "tr": "37i9dQZEVXbMIJZxwqzod6",
}

async def test_playlist_scraping():
    """Test Spotify playlist scraping with Playwright."""
    print("="*60)
    print("Testing Spotify Playlist HTML Scraping")
    print("="*60)
    print()
    
    for country, playlist_id in PLAYLISTS.items():
        country_name = "Netherlands" if country == "nl" else "Turkey"
        
        print(f"\n{'='*60}")
        print(f"Testing {country_name} playlist: {playlist_id}")
        print(f"{'='*60}")
        
        try:
            print(f"\nScraping playlist...")
            result: SpotifyResult = await fetch_spotify_tracks_scraper(
                limit=20,
                country=country,
            )
            
            if result.tracks:
                print(f"✓ Successfully scraped {len(result.tracks)} tracks")
                print(f"\nFirst 5 tracks:")
                for i, track in enumerate(result.tracks[:5], 1):
                    print(f"  {i}. {track.artist} - {track.title}")
                    print(f"     URL: {track.url}")
                    print(f"     Published: {track.published_at}")
            else:
                print(f"✗ No tracks found")
                if result.unavailable_reason:
                    print(f"  Reason: {result.unavailable_reason}")
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_playlist_scraping())
