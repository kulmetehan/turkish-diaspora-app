# Spotify Playlist Scraping Implementation

## Overview

The Spotify Viral 50 playlist scraper uses browser automation (Playwright) to scrape JavaScript-rendered playlist pages, as Spotify's Web API restricts access to editorial playlists for new applications.

## Background

As of November 27, 2024, Spotify restricted access to algorithmic and Spotify-managed editorial playlists (like Viral 50) for new applications in development mode.

**Reference:** [Spotify Developer Blog - Changes to the Web API](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)

## Affected Playlists

- **Netherlands Viral 50**: `37i9dQZEVXbMQaPQjt027d`
- **Turkey Viral 50**: `37i9dQZEVXbMIJZxwqzod6`

## Current Implementation

The scraper (`Backend/services/news_trending_spotify_scraper.py`) uses:

1. **Playwright Browser Automation** (Primary):
   - Loads playlist pages in headless Chromium browser
   - Waits for JavaScript rendering to complete
   - Extracts track data from DOM elements using multiple selector strategies
   - Most reliable method for JavaScript-rendered content

2. **Embedded JSON Parsing** (Fallback):
   - Extracts JSON data from script tags after page load
   - Parses playlist tracks from embedded JSON structures
   - Used if DOM scraping fails

## Architecture

```
┌─────────────────────────────────────────┐
│  SpotifyScraper (Playwright)            │
│  ┌───────────────────────────────────┐ │
│  │ 1. Load playlist page in browser  │ │
│  │ 2. Wait for JavaScript rendering   │ │
│  │ 3. Extract track data from DOM     │ │
│  │ 4. Parse embedded JSON if needed   │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│  SpotifyResult (tracks + metadata)     │
└─────────────────────────────────────────┘
```

## Features

- **Headless Browser**: Uses Chromium in headless mode for CI/CD compatibility
- **Multiple Selector Strategies**: Tries various CSS selectors to find track elements
- **Error Handling**: Graceful fallback to embedded JSON parsing
- **Caching**: 3-minute cache to minimize requests
- **Rate Limiting**: Single concurrent request to avoid overloading

## Dependencies

- `playwright==1.48.0`: Browser automation library
- Requires Chromium browser installation (via `playwright install chromium`)

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

3. For CI/CD (GitHub Actions), browsers are installed automatically in the workflow.

## Testing

Run the test script to verify playlist scraping:
```bash
cd Backend
python3 scripts/test_spotify_playlist.py
```

## Error Handling

- **Browser launch failures**: Logged and returns unavailable_reason
- **Timeout errors**: Logged and retries with longer timeout
- **Selector not found**: Falls back to embedded JSON parsing
- **Network errors**: Logged and returns unavailable_reason

## Limitations

- **Slower than API**: Browser automation is slower than direct API calls
- **Resource intensive**: Requires more memory and CPU than HTTP requests
- **Selector dependencies**: May break if Spotify changes DOM structure
- **Anti-bot detection**: Spotify may detect and block automated browsers

## Mitigation Strategies

1. **Multiple Selectors**: Uses various CSS selectors to find tracks
2. **Embedded JSON Fallback**: Falls back to JSON parsing if DOM scraping fails
3. **Caching**: Reduces number of requests with 3-minute cache
4. **Realistic Headers**: Sets realistic user agent and headers
5. **Headless Mode**: Uses headless browser to reduce resource usage

## Future Improvements

- Monitor selector changes and update as needed
- Consider using stealth mode if anti-bot detection becomes an issue
- Optimize browser launch/shutdown for better performance
- Add retry logic with exponential backoff

## Configuration

No environment variables required. The scraper works without API credentials.

## Worker Execution

The scraper runs daily via GitHub Actions workflow:
- Schedule: Daily at 02:00 UTC
- Workflow: `.github/workflows/tda_spotify_scraper.yml`
- Worker: `Backend/app/workers/news_spotify_scraper_worker.py`
