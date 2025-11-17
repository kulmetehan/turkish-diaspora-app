# -*- coding: utf-8 -*-
"""
OsmPlacesService — Enhanced Overpass API integration for discovery
- Builds Overpass QL queries for nodes/ways/relations in a circle
- Translates categories.yml osm_tags into OR/AND filters
- Normalizes results to internal place shape
- Handles rate limiting, endpoint rotation, and robust retry/backoff
- Supports adaptive cell subdivision and Turkish hints filtering
- Full OSM/Overpass policy compliance
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import time
import uuid
from json import JSONDecodeError
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlencode

import httpx
import structlog

logger = structlog.get_logger()

# Environment configuration
OSM_LOG_QUERIES = os.getenv("OSM_LOG_QUERIES", "false").lower() == "true"
OSM_TRACE = os.getenv("OSM_TRACE", "0") == "1"

def _trace(msg: str):
    """Debug tracing for OSM service."""
    if OSM_TRACE:
        print(f"[OSM_TRACE] {msg}")

# Overpass endpoint pool for rotation
# Can be overridden via OVERPASS_ENDPOINTS env var (comma-separated URLs)
_ENDPOINTS_STR = os.getenv("OVERPASS_ENDPOINTS", "")
if _ENDPOINTS_STR:
    OVERPASS_ENDPOINTS = [url.strip() for url in _ENDPOINTS_STR.split(",") if url.strip()]
else:
    OVERPASS_ENDPOINTS = [
        "https://overpass-api.de/api/interpreter",
        "https://z.overpass-api.de/api/interpreter", 
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.openstreetmap.ru/api/interpreter",
    ]

# Default configuration
DEFAULT_USER_AGENT = "TurkishDiasporaApp/1.0 (contact: m.kul@lamarka.nl)"
DEFAULT_TIMEOUT_S = int(os.getenv("OVERPASS_REQUEST_TIMEOUT_SECONDS", os.getenv("OVERPASS_TIMEOUT_S", "45")))
DEFAULT_MAX_RESULTS = int(os.getenv("DISCOVERY_MAX_RESULTS", "25"))
DEFAULT_RATE_LIMIT_QPS = float(os.getenv("DISCOVERY_RATE_LIMIT_QPS", "0.15"))
DEFAULT_SLEEP_BASE_S = float(os.getenv("DISCOVERY_SLEEP_BASE_S", "3.0"))
DEFAULT_SLEEP_JITTER_PCT = float(os.getenv("DISCOVERY_SLEEP_JITTER_PCT", "0.20"))
DEFAULT_BACKOFF_SERIES = [int(x) for x in os.getenv("DISCOVERY_BACKOFF_SERIES", "20,60,180,420").split(",")]
DEFAULT_MAX_SUBDIVIDE_DEPTH = int(os.getenv("MAX_SUBDIVIDE_DEPTH", "2"))
DEFAULT_TURKISH_HINTS = os.getenv("OSM_TURKISH_HINTS", "1").lower() == "true"

# New Overpass safety configuration (industry-grade defaults)
DEFAULT_MAX_CONCURRENT_PER_ENDPOINT = int(os.getenv("OVERPASS_MAX_CONCURRENT_PER_ENDPOINT", "1"))
DEFAULT_MIN_DELAY_SECONDS = float(os.getenv("OVERPASS_MIN_DELAY_SECONDS", "8"))
DEFAULT_MAX_RETRIES = int(os.getenv("OVERPASS_MAX_RETRIES", "2"))
DEFAULT_BACKOFF_BASE_SECONDS = float(os.getenv("OVERPASS_BACKOFF_BASE_SECONDS", "2"))
DEFAULT_BACKOFF_JITTER_FRACTION = float(os.getenv("OVERPASS_BACKOFF_JITTER_FRACTION", "0.3"))
DEFAULT_ENABLE_ENDPOINT_FALLBACK = os.getenv("OVERPASS_ENABLE_ENDPOINT_FALLBACK", "false").lower() == "true"
OVERPASS_PRIMARY_ENDPOINT = os.getenv("OVERPASS_PRIMARY_ENDPOINT")  # Optional override

# Module-level per-endpoint concurrency control
# These dictionaries are shared across all OsmPlacesService instances to enforce
# global rate limits per Overpass endpoint (respecting public usage guidelines:
# ≤10k queries/day, ≤1GB/day, max 1 concurrent request per endpoint)
_endpoint_semaphores: Dict[str, asyncio.Semaphore] = {}
_endpoint_last_request: Dict[str, float] = {}
_semaphore_lock = asyncio.Lock()  # Protects semaphore dictionary initialization

# Rate limiting
class TokenBucket:
    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
    
    async def acquire(self, tokens: float = 1.0) -> None:
        now = time.time()
        # Refill tokens based on time elapsed
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        
        if self.tokens < tokens:
            sleep_time = (tokens - self.tokens) / self.refill_rate
            await asyncio.sleep(sleep_time)
            self.tokens = 0
        else:
            self.tokens -= tokens

class OsmPlacesService:
    def __init__(
        self,
        endpoint: Optional[str] = None,
        timeout_s: int = DEFAULT_TIMEOUT_S,
        rate_limit_qps: float = DEFAULT_RATE_LIMIT_QPS,
        user_agent: Optional[str] = None,
        max_results: int = DEFAULT_MAX_RESULTS,
        sleep_base_s: float = DEFAULT_SLEEP_BASE_S,
        sleep_jitter_pct: float = DEFAULT_SLEEP_JITTER_PCT,
        backoff_series: List[int] = DEFAULT_BACKOFF_SERIES,
        turkish_hints: bool = DEFAULT_TURKISH_HINTS,
        max_subdivide_depth: int = DEFAULT_MAX_SUBDIVIDE_DEPTH
    ):
        self.endpoints = OVERPASS_ENDPOINTS.copy()
        self.current_endpoint_index = 0
        
        # Use primary endpoint override if provided, otherwise use passed endpoint or default
        if OVERPASS_PRIMARY_ENDPOINT:
            self.endpoint = OVERPASS_PRIMARY_ENDPOINT
        elif endpoint:
            self.endpoint = endpoint
        else:
            self.endpoint = self.endpoints[0]
            
        self.timeout_s = timeout_s
        self.user_agent = user_agent or os.getenv("OVERPASS_USER_AGENT", DEFAULT_USER_AGENT)
        self.max_results = max_results
        self.sleep_base_s = sleep_base_s
        self.sleep_jitter_pct = sleep_jitter_pct
        self.backoff_series = backoff_series
        self.turkish_hints = turkish_hints
        self.max_subdivide_depth = max_subdivide_depth
        
        # Legacy rate limiter (kept for backward compat, but superseded by per-endpoint semaphore + delay)
        self.rate_limiter = TokenBucket(capacity=1.0, refill_rate=rate_limit_qps)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_s),
            headers={"User-Agent": self.user_agent}
        )
        
        # Telemetry uses shared asyncpg helpers (no per-instance pool)
        self._db_session = None  # kept for backward compat; unused

    async def aclose(self):
        await self._client.aclose()
        if self._db_session:
            await self._db_session.close()

    async def _get_endpoint_semaphore(self, endpoint: str) -> asyncio.Semaphore:
        """
        Get or create a semaphore for the given endpoint.
        Ensures max concurrent requests per endpoint is enforced globally.
        """
        async with _semaphore_lock:
            if endpoint not in _endpoint_semaphores:
                max_concurrent = DEFAULT_MAX_CONCURRENT_PER_ENDPOINT
                _endpoint_semaphores[endpoint] = asyncio.Semaphore(max_concurrent)
            return _endpoint_semaphores[endpoint]

    async def _enforce_min_delay(self, endpoint: str) -> None:
        """
        Enforce minimum delay since last request to this endpoint.
        Respects Overpass public usage guidelines (≤1 request per 5-10s).
        """
        if endpoint in _endpoint_last_request:
            elapsed = time.time() - _endpoint_last_request[endpoint]
            min_delay = DEFAULT_MIN_DELAY_SECONDS
            if elapsed < min_delay:
                sleep_time = min_delay - elapsed
                _trace(f"enforcing min delay: sleeping {sleep_time:.2f}s for {endpoint}")
                await asyncio.sleep(sleep_time)
        _endpoint_last_request[endpoint] = time.time()

    def _categorize_error_message(self, error: Exception, status_code: Optional[int] = None) -> str:
        """
        Categorize error messages with standardized prefixes for metrics analysis.
        Returns prefixed error message string.
        """
        error_str = str(error) if error else ""
        
        # Network disconnects (status_code 0 or specific error messages)
        if status_code == 0 or "Server disconnected without sending a response" in error_str:
            return f"DISCONNECT: Server disconnected without sending a response."
        
        # Timeouts (504 or timeout exceptions)
        if status_code == 504 or isinstance(error, (httpx.TimeoutException, asyncio.TimeoutError)):
            return f"TIMEOUT: HTTP 504"
        
        # Rate limiting (429)
        if status_code == 429:
            return f"RATE_LIMIT: HTTP 429"
        
        # Other 5xx server errors
        if status_code and status_code >= 500:
            return f"SERVER_5XX: HTTP {status_code}"
        
        # Network errors (connection issues, etc.)
        if isinstance(error, (httpx.ConnectError, httpx.NetworkError)) or "network" in error_str.lower():
            return f"NETWORK_ERROR: {error_str[:200]}"
        
        # Generic fallback
        if status_code:
            return f"HTTP_ERROR: HTTP {status_code} - {error_str[:200]}"
        
        return f"ERROR: {error_str[:200]}"

    def _parse_overpass_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse Overpass response with defensive JSON handling."""
        _trace(f"endpoint={self.endpoint} status={response.status_code}")
        
        # Always parse JSON to a dict
        data: Dict[str, Any]
        try:
            data = response.json()
        except JSONDecodeError:
            # Some mirrors return text errors; record them in telemetry and raise
            snippet = (response.text or "")[:500]
            _trace(f"body[:400]={snippet!r}")
            raise RuntimeError(f"Overpass JSON decode failed (status={response.status_code}). Body[:500]={snippet!r}")

        # Overpass success payloads always have 'elements' list (even empty)
        elements = data.get("elements")
        if isinstance(elements, str):
            # Defensive: some wrapping layer might have serialized elements to a string
            try:
                data["elements"] = json.loads(elements)
            except JSONDecodeError:
                # Fall back to empty list; upstream code won't crash
                data["elements"] = []
        elif elements is None:
            data["elements"] = []

        _trace(f"elements_type={type(data.get('elements')).__name__} len={len(data.get('elements', [])) if isinstance(data.get('elements'), list) else 'n/a'}")
        
        return data

    def _rotate_endpoint(self):
        """Rotate to the next endpoint in the pool."""
        self.current_endpoint_index = (self.current_endpoint_index + 1) % len(self.endpoints)
        self.endpoint = self.endpoints[self.current_endpoint_index]
        logger.info("osm_endpoint_rotated", new_endpoint=self.endpoint)

    def _get_turkish_hints_filters(self) -> List[str]:
        """Get additional filters for Turkish hints when enabled."""
        if not self.turkish_hints:
            return []
        
        # Turkish cuisine and food-related filters
        turkish_filters = [
            '["cuisine"="turkish"]',
            '["name"~"kebab|döner|doner|baklava|börek|borek|simit|pide|lahmacun|ocakbaşı|ocakbasi|lokum",i]',
            '["name:tr"]'
        ]
        return turkish_filters

    async def _log_overpass_call(
        self,
        endpoint: str,
        bbox_or_center: str,
        radius_m: int,
        query_bytes: int,
        status_code: int,
        found: int,
        normalized: int,
        category_set: List[str],
        cell_id: str,
        attempt: int,
        duration_ms: int,
        error_message: Optional[str] = None,
        retry_after_s: Optional[int] = None,
        raw_preview: Optional[str] = None,
        raw_preview_json: Optional[Dict[str, Any]] = None,
    ):
        """Log Overpass API call to database for telemetry."""
        try:
            from services.db_service import execute

            # Create safe preview string for DB storage
            safe_preview = None
            if raw_preview is not None:
                try:
                    # raw_preview is expected to be pre-truncated at construction time
                    safe_preview = str(raw_preview)
                except Exception:
                    safe_preview = "preview_error"

            sql = (
                """
                INSERT INTO overpass_calls (
                    endpoint, bbox_or_center, radius_m, query_bytes, status_code,
                    found, normalized, category_set, cell_id, attempt, duration_ms,
                    error_message, retry_after_s, user_agent, timeout_s, max_results, raw_preview, raw_preview_json
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8, $9, $10, $11,
                    $12, $13, $14, $15, $16, $17, $18
                )
                """
            )
            await execute(
                sql,
                endpoint,
                bbox_or_center,
                int(radius_m),
                int(query_bytes),
                int(status_code),
                int(found),
                int(normalized),
                category_set or [],
                cell_id,
                int(attempt),
                int(duration_ms),
                error_message,
                retry_after_s,
                self.user_agent,
                int(self.timeout_s),
                int(self.max_results),
                safe_preview,
                raw_preview_json,
            )
        except Exception as e:
            logger.warning("osm_telemetry_log_failed", error=str(e))

    def _generate_cell_id(self, lat: float, lng: float, radius: int) -> str:
        """Generate a unique cell ID for tracking."""
        # Round coordinates to create consistent cell boundaries
        lat_rounded = round(lat, 4)
        lng_rounded = round(lng, 4)
        return f"{lat_rounded}_{lng_rounded}_{radius}"

    def _subdivide_cell(self, lat: float, lng: float, radius: int) -> List[Tuple[float, float, int]]:
        """Subdivide a cell into 4 smaller subcells."""
        # Calculate half radius for subdivision
        half_radius = radius // 2
        if half_radius < 250:  # Minimum cell size
            return []
        
        # Calculate offset for subcells
        lat_offset = (radius / 111320.0) * 0.5  # Approximate meters to degrees
        lng_offset = (radius / (111320.0 * abs(lat))) * 0.5
        
        subcells = []
        for lat_mult in [-1, 1]:
            for lng_mult in [-1, 1]:
                sub_lat = lat + (lat_mult * lat_offset)
                sub_lng = lng + (lng_mult * lng_offset)
                subcells.append((sub_lat, sub_lng, half_radius))
        
        return subcells

    def _render_filters_any(self, tag_dicts: List[Dict[str, str]]) -> List[str]:
        """Render OR conditions - returns multiple selectors (one per tag_dict)."""
        selectors = []
        for tag_dict in tag_dicts:
            for key, value in tag_dict.items():
                selectors.append(f'["{key}"="{value}"]')
        return selectors

    def _render_filters_all(self, tag_dicts: List[Dict[str, str]]) -> str:
        """Render AND conditions - returns a single selector with chained filters."""
        filters = []
        for tag_dict in tag_dicts:
            for key, value in tag_dict.items():
                filters.append(f'["{key}"="{value}"]')
        return "".join(filters)

    def _render_union_selectors(self, lat: float, lng: float, radius: int, filter_snippets: List[str]) -> str:
        """Create a union combining node/way/relation for EACH filter snippet."""
        union_parts = []
        for filter_snippet in filter_snippets:
            union_parts.extend([
                f"  node{filter_snippet}(around:{radius},{lat:.6f},{lng:.6f});",
                f"  way{filter_snippet}(around:{radius},{lat:.6f},{lng:.6f});",
                f"  relation{filter_snippet}(around:{radius},{lat:.6f},{lng:.6f});"
            ])
        
        return "(\n" + "\n".join(union_parts) + "\n);"

    def _build_union_query(
        self,
        lat: float,
        lng: float,
        radius: int,
        osm_tags_list: List[List[Dict[str, Any]]],
        max_results: int,
        timeout_s: int = 25
    ) -> str:
        """
        Build a single Overpass query that combines multiple categories.
        
        Query design choices (for Overpass safety compliance):
        - Uses `(around:radius,lat,lng)` selector instead of bbox to limit result size
        - Queries node/way/relation in union to ensure complete coverage
        - Includes `[timeout:...]` directive to prevent runaway queries
        - Limits output with `out center {max_results}` to avoid large payloads
        - Smaller radius (typically 1000m) prevents overwhelming Overpass servers
        
        These choices respect Overpass public usage guidelines (≤10k queries/day, ≤1GB/day).
        """
        all_filter_snippets = []
        
        # Collect all filter snippets from all categories
        for osm_tags in osm_tags_list:
            for tag_group in osm_tags:
                if "any" in tag_group:
                    any_selectors = self._render_filters_any(tag_group["any"])
                    all_filter_snippets.extend(any_selectors)
                elif "all" in tag_group:
                    all_selector = self._render_filters_all(tag_group["all"])
                    all_filter_snippets.append(all_selector)
        
        # Add Turkish hints if enabled
        turkish_filters = self._get_turkish_hints_filters()
        all_filter_snippets.extend(turkish_filters)
        
        if not all_filter_snippets:
            # Fallback to basic place types if no filters
            all_filter_snippets = ['["amenity"]', '["shop"]', '["office"]']
        
        union_block = self._render_union_selectors(lat, lng, radius, all_filter_snippets)
        
        query = f"""
[out:json][timeout:{timeout_s}];
{union_block}
out center {max_results};
""".strip()
        
        return query

    def _build_overpass_query(
        self,
        lat: float,
        lng: float,
        radius: int,
        osm_tags: List[Dict[str, Any]],
        max_results: int,
        timeout_s: int = 25
    ) -> str:
        """Build Overpass QL query for the given parameters."""
        filter_snippets = []
        
        for tag_group in osm_tags:
            if "any" in tag_group:
                # OR conditions - multiple selectors
                any_selectors = self._render_filters_any(tag_group["any"])
                filter_snippets.extend(any_selectors)
            elif "all" in tag_group:
                # AND conditions - single selector
                all_selector = self._render_filters_all(tag_group["all"])
                filter_snippets.append(all_selector)
        
        if not filter_snippets:
            # Fallback to basic place types if no filters
            filter_snippets = ['["amenity"]', '["shop"]', '["office"]']
        
        union_block = self._render_union_selectors(lat, lng, radius, filter_snippets)
        
        query = f"""
[out:json][timeout:{timeout_s}];
{union_block}
out center;
""".strip()
        
        return query

    def _normalize_osm_result(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize OSM element to internal place shape with defensive type checking."""
        # Defensive: ensure element is a dict
        if not isinstance(element, dict):
            _trace(f"skipping non-dict element: {type(element).__name__}")
            return None
        
        # Extract basic info with safe defaults
        element_type = element.get("type", "node")
        element_id = element.get("id", 0)
        
        # Build unique ID
        unique_id = f"{element_type}/{element_id}"
        
        # Extract name (prefer name, then brand, then operator, then fallback)
        tags = element.get("tags", {})
        if not isinstance(tags, dict):
            tags = {}
            
        name = (
            tags.get("name") or
            tags.get("brand") or
            tags.get("operator") or
            "Unnamed"
        )
        
        # Build address
        address_parts = []
        if tags.get("addr:street"):
            street = tags["addr:street"]
            if tags.get("addr:housenumber"):
                street += f" {tags['addr:housenumber']}"
            address_parts.append(street)
        if tags.get("addr:postcode"):
            address_parts.append(tags["addr:postcode"])
        if tags.get("addr:city"):
            address_parts.append(tags["addr:city"])
        
        formatted_address = ", ".join(address_parts) if address_parts else None
        
        # Extract coordinates
        if element_type == "node":
            lat = element.get("lat")
            lng = element.get("lon")
        else:
            # For ways/relations, use center if available
            center = element.get("center", {})
            if isinstance(center, dict):
                lat = center.get("lat")
                lng = center.get("lon")
            else:
                lat = lng = None
        
        # Build types list from tags (informational)
        types = []
        for key, value in tags.items():
            if key in ["amenity", "shop", "office", "tourism", "leisure", "religion"]:
                types.append(f"{key}={value}")
        
        return {
            "id": unique_id,
            "displayName": {"text": name},
            "formattedAddress": formatted_address,
            "location": {"lat": lat, "lng": lng} if lat is not None and lng is not None else None,
            "types": types,
            "rating": None,
            "userRatingCount": None,
            "businessStatus": None,
            "websiteUri": tags.get("website")
        }

    async def search_nearby(
        self,
        *,
        lat: float,
        lng: float,
        radius: int,
        included_types: Optional[List[str]] = None,
        max_results: Optional[int] = None,
        language: Optional[str] = None,
        category_osm_tags: Optional[List[List[Dict[str, Any]]]] = None,
        cell_id: Optional[str] = None,
        attempt: int = 1
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Search for places near the given coordinates using Overpass API with robust retry logic.
        
        Args:
            lat: Latitude
            lng: Longitude  
            radius: Search radius in meters
            included_types: List of category keys from categories.yml (not used directly)
            max_results: Maximum number of results to return (uses self.max_results if None)
            language: Language preference (not used by Overpass)
            category_osm_tags: List of OSM tag configurations for each category
            cell_id: Unique identifier for this cell (for telemetry)
            attempt: Attempt number for this cell
            
        Returns:
            Tuple of (normalized place dictionaries, needs_subdivision)
        """
        if max_results is None:
            max_results = self.max_results
            
        if cell_id is None:
            cell_id = self._generate_cell_id(lat, lng, radius)
        
        # Rate limiting is now handled via per-endpoint semaphore + min delay in _make_request
        # Legacy TokenBucket and fixed sleep are replaced by industry-grade controls
        
        # Use provided OSM tags or fallback to basic types
        if category_osm_tags:
            osm_tags_list = category_osm_tags
        else:
            # Fallback to basic place types
            osm_tags_list = [[{
                "any": [
                    {"amenity": "restaurant"},
                    {"shop": "bakery"},
                    {"shop": "supermarket"},
                    {"shop": "hairdresser"},
                    {"amenity": "place_of_worship"},
                    {"office": "travel_agent"}
                ]
            }]]
        
        query = self._build_union_query(lat, lng, radius, osm_tags_list, max_results, self.timeout_s)
        
        if OSM_LOG_QUERIES:
            logger.debug("osm_query_rendered", provider="osm", query=query)
        
        logger.info(
            "osm_search_start",
            provider="osm",
            lat=lat,
            lng=lng,
            radius=radius,
            max_results=max_results,
            query_length=len(query),
            cell_id=cell_id,
            attempt=attempt
        )
        
        # Get semaphore for this endpoint (enforces max concurrent requests)
        semaphore = await self._get_endpoint_semaphore(self.endpoint)
        
        # Retry logic with exponential backoff
        max_retries = DEFAULT_MAX_RETRIES
        backoff_base = DEFAULT_BACKOFF_BASE_SECONDS
        jitter_frac = DEFAULT_BACKOFF_JITTER_FRACTION
        last_exception = None
        last_status_code = None
        retry_after_s = None
        
        for retry_attempt in range(max_retries + 1):  # 0 to max_retries (inclusive)
            current_attempt = retry_attempt + 1
            start_time = time.time()
            status_code = 0
            error_message = None
            should_retry = False
            
            try:
                # Acquire semaphore and enforce minimum delay between requests
                async with semaphore:
                    await self._enforce_min_delay(self.endpoint)
                    
                    # Make the request with proper form encoding
                    response = await self._client.post(
                        self.endpoint,
                        data={'data': query},
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                            "User-Agent": self.user_agent
                        }
                    )
                    
                    status_code = response.status_code
                    last_status_code = status_code
                    
                    # Handle non-retryable errors (4xx except 429)
                    if status_code in (400, 422):
                        error_message = self._categorize_error_message(
                            RuntimeError("Syntax error"), status_code
                        )
                        logger.error(
                            "osm_query_syntax_error",
                            provider="osm",
                            status_code=status_code,
                            query=query,
                            response_text=response.text[:500]
                        )
                        # Log and return empty (don't retry syntax errors)
                        duration_ms = int((time.time() - start_time) * 1000)
                        await self._log_overpass_call(
                            endpoint=self.endpoint,
                            bbox_or_center=f"{lat},{lng}",
                            radius_m=radius,
                            query_bytes=len(query),
                            status_code=status_code,
                            found=0,
                            normalized=0,
                            category_set=included_types or [],
                            cell_id=cell_id,
                            attempt=current_attempt,
                            duration_ms=duration_ms,
                            error_message=error_message,
                        )
                        return [], False
                    
                    # Handle rate limiting (429) - retryable
                    if status_code == 429:
                        retry_after_s = int(response.headers.get("Retry-After", "60"))
                        retry_after_s = min(retry_after_s, 60)  # Cap to 60s
                        error_message = self._categorize_error_message(
                            httpx.HTTPStatusError("Rate limited", request=response.request, response=response),
                            status_code
                        )
                        logger.warning(
                            "osm_rate_limited",
                            provider="osm",
                            retry_after=retry_after_s,
                            attempt=current_attempt,
                            max_retries=max_retries
                        )
                        should_retry = retry_attempt < max_retries
                        last_exception = httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
                        if not should_retry:
                            raise last_exception
                    
                    # Handle server errors (5xx) - retryable
                    elif status_code >= 500:
                        error_message = self._categorize_error_message(
                            httpx.HTTPStatusError("Server error", request=response.request, response=response),
                            status_code
                        )
                        logger.error(
                            "osm_server_error",
                            provider="osm",
                            status_code=status_code,
                            attempt=current_attempt,
                            max_retries=max_retries
                        )
                        should_retry = retry_attempt < max_retries
                        last_exception = httpx.HTTPStatusError("Server error", request=response.request, response=response)
                        if not should_retry:
                            raise last_exception
                    
                    # Success case
                    else:
                        response.raise_for_status()
                        
                        # Use defensive JSON parsing
                        data = self._parse_overpass_response(response)
                        elements = data.get("elements", [])
                        
                        # Defensive conversions for elements
                        if isinstance(elements, str):
                            try:
                                elements = json.loads(elements)
                            except Exception:
                                elements = []
                        elif not isinstance(elements, list):
                            elements = []
                        
                        # Normalize results with defensive element handling
                        normalized = []
                        for element in elements:
                            try:
                                # Skip non-dict elements safely
                                if not isinstance(element, dict):
                                    _trace(f"skipping non-dict element: {type(element).__name__}")
                                    continue
                                    
                                normalized_element = self._normalize_osm_result(element)
                                if normalized_element and normalized_element.get("location"):  # Only include if we have coordinates
                                    normalized.append(normalized_element)
                            except Exception as e:
                                logger.warning(
                                    "osm_normalization_error",
                                    provider="osm",
                                    element_id=element.get("id") if isinstance(element, dict) else "unknown",
                                    error=str(e)
                                )
                                continue
                        
                        # Limit results
                        result = normalized[:max_results]
                        
                        # Check if we need subdivision (found >= max_results)
                        needs_subdivision = len(elements) >= max_results
                        
                        duration_ms = int((time.time() - start_time) * 1000)
                        
                        # Log successful call with raw preview
                        raw_preview = None
                        preview_json: Optional[Dict[str, Any]] = None
                        try:
                            # Human-readable snippet (may be invalid JSON if cut mid-structure)
                            if data:
                                raw_preview = json.dumps(data)[:4000]
                            else:
                                raw_preview = None
                        except Exception:
                            raw_preview = (str(data)[:4000]) if data else None

                        # Build compact, always-valid JSON summary
                        try:
                            N = 20
                            total_elements: Optional[int] = None
                            elems: List[Any] = []
                            if isinstance(data, dict) and "elements" in data:
                                if isinstance(data.get("elements"), list):
                                    elems = data.get("elements")  # type: ignore[assignment]
                                    total_elements = len(elems)
                                else:
                                    # elements exists but is not a list
                                    total_elements = None
                                    elems = []
                            elif isinstance(data, dict):
                                # no elements key
                                total_elements = None
                                elems = []
                            else:
                                # non-dict or None
                                total_elements = None
                                elems = []

                            preview_elements = elems[:N] if isinstance(elems, list) else []
                            truncated_flag = (isinstance(total_elements, int) and total_elements > N)

                            meta = {}
                            if isinstance(data, dict):
                                if "version" in data:
                                    meta["version"] = data.get("version")
                                if "generator" in data:
                                    meta["generator"] = data.get("generator")

                            preview_json = {
                                "truncated": bool(truncated_flag),
                                "total_elements": total_elements,
                                "preview_elements": preview_elements,
                                "meta": meta or None,
                            }
                        except Exception:
                            preview_json = {"truncated": None, "error": "preview_json_build_failed"}
                            
                        await self._log_overpass_call(
                            endpoint=self.endpoint,
                            bbox_or_center=f"{lat},{lng}",
                            radius_m=radius,
                            query_bytes=len(query),
                            status_code=status_code,
                            found=len(elements),
                            normalized=len(result),
                            category_set=included_types or [],
                            cell_id=cell_id,
                            attempt=current_attempt,
                            duration_ms=duration_ms,
                            raw_preview=raw_preview,
                            raw_preview_json=preview_json,
                        )
                        
                        logger.info(
                            "osm_search_success",
                            provider="osm",
                            found=len(elements),
                            normalized=len(result),
                            lat=lat,
                            lng=lng,
                            needs_subdivision=needs_subdivision,
                            duration_ms=duration_ms,
                            attempt=current_attempt
                        )
                        
                        return result, needs_subdivision
                        
            except httpx.TimeoutException as e:
                duration_ms = int((time.time() - start_time) * 1000)
                status_code = 504
                error_message = self._categorize_error_message(e, status_code)
                last_exception = e
                last_status_code = status_code
                should_retry = retry_attempt < max_retries
                
                # Log timeout attempt
                await self._log_overpass_call(
                    endpoint=self.endpoint,
                    bbox_or_center=f"{lat},{lng}",
                    radius_m=radius,
                    query_bytes=len(query),
                    status_code=status_code,
                    found=0,
                    normalized=0,
                    category_set=included_types or [],
                    cell_id=cell_id,
                    attempt=current_attempt,
                    duration_ms=duration_ms,
                    error_message=error_message,
                )
                
                logger.warning(
                    "osm_search_timeout",
                    provider="osm",
                    lat=lat,
                    lng=lng,
                    attempt=current_attempt,
                    max_retries=max_retries,
                    will_retry=should_retry
                )
                
                if not should_retry:
                    # Final attempt failed - optionally rotate endpoint if enabled
                    if DEFAULT_ENABLE_ENDPOINT_FALLBACK:
                        self._rotate_endpoint()
                    return [], False
                    
            except (httpx.HTTPStatusError, httpx.NetworkError, httpx.ConnectError) as e:
                # Handle retryable HTTP errors that weren't caught above
                # This catches cases where should_retry was set but exception needs to propagate for retry logic
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Determine status code from exception
                exc_status_code = None
                if hasattr(e, 'response') and e.response:
                    exc_status_code = e.response.status_code
                elif last_status_code:
                    exc_status_code = last_status_code
                
                if error_message is None:
                    error_message = self._categorize_error_message(e, exc_status_code)
                
                # Log this attempt
                await self._log_overpass_call(
                    endpoint=self.endpoint,
                    bbox_or_center=f"{lat},{lng}",
                    radius_m=radius,
                    query_bytes=len(query),
                    status_code=exc_status_code or 0,
                    found=0,
                    normalized=0,
                    category_set=included_types or [],
                    cell_id=cell_id,
                    attempt=current_attempt,
                    duration_ms=duration_ms,
                    error_message=error_message,
                    retry_after_s=retry_after_s,
                )
                
                if not should_retry:
                    # Final attempt failed
                    logger.error(
                        "osm_search_error_final",
                        provider="osm",
                        error=error_message,
                        lat=lat,
                        lng=lng,
                        status_code=exc_status_code,
                        attempts=current_attempt
                    )
                    
                    # Optionally rotate endpoint if enabled
                    if DEFAULT_ENABLE_ENDPOINT_FALLBACK:
                        self._rotate_endpoint()
                    
                    return [], False
                
                # If should_retry is True, exception will propagate and we'll continue to backoff logic below
                
            except Exception as e:
                # Unexpected error - log and return empty (don't retry unknown errors)
                duration_ms = int((time.time() - start_time) * 1000)
                error_message = self._categorize_error_message(e, None)
                
                await self._log_overpass_call(
                    endpoint=self.endpoint,
                    bbox_or_center=f"{lat},{lng}",
                    radius_m=radius,
                    query_bytes=len(query),
                    status_code=0,
                    found=0,
                    normalized=0,
                    category_set=included_types or [],
                    cell_id=cell_id,
                    attempt=current_attempt,
                    duration_ms=duration_ms,
                    error_message=error_message
                )
                
                logger.error(
                    "osm_search_error_unexpected",
                    provider="osm",
                    error=error_message,
                    lat=lat,
                    lng=lng,
                    error_type=type(e).__name__
                )
                
                return [], False
            
            # Calculate backoff and retry
            if should_retry:
                # For 429, respect Retry-After header if present
                if last_status_code == 429 and retry_after_s:
                    wait_time = retry_after_s
                else:
                    # Exponential backoff: base * 2^(attempt)
                    wait_time = backoff_base * (2 ** retry_attempt)
                
                # Add jitter
                jitter = random.uniform(0, wait_time * jitter_frac)
                total_wait = wait_time + jitter
                
                logger.info(
                    "osm_retry_backoff",
                    provider="osm",
                    attempt=current_attempt,
                    max_retries=max_retries,
                    wait_seconds=total_wait,
                    endpoint=self.endpoint
                )
                
                await asyncio.sleep(total_wait)
        
        # Should never reach here, but safety fallback
        return [], False

    async def search_nearby_with_subdivision(
        self,
        *,
        lat: float,
        lng: float,
        radius: int,
        included_types: Optional[List[str]] = None,
        max_results: Optional[int] = None,
        language: Optional[str] = None,
        category_osm_tags: Optional[List[List[Dict[str, Any]]]] = None,
        max_depth: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for places with adaptive cell subdivision when results are capped.
        
        Args:
            lat: Latitude
            lng: Longitude  
            radius: Search radius in meters
            included_types: List of category keys from categories.yml
            max_results: Maximum number of results to return
            language: Language preference (not used by Overpass)
            category_osm_tags: List of OSM tag configurations for each category
            max_depth: Maximum subdivision depth (uses self.max_subdivide_depth if None)
            
        Returns:
            List of normalized place dictionaries
        """
        if max_depth is None:
            max_depth = self.max_subdivide_depth
            
        all_results = []
        cells_to_process = [(lat, lng, radius, 0)]  # (lat, lng, radius, depth)
        
        while cells_to_process:
            current_lat, current_lng, current_radius, current_depth = cells_to_process.pop(0)
            
            # Generate cell ID for tracking
            cell_id = self._generate_cell_id(current_lat, current_lng, current_radius)
            
            # Search this cell
            results, needs_subdivision = await self.search_nearby(
                lat=current_lat,
                lng=current_lng,
                radius=current_radius,
                included_types=included_types,
                max_results=max_results,
                language=language,
                category_osm_tags=category_osm_tags,
                cell_id=cell_id,
                attempt=1
            )
            
            all_results.extend(results)
            
            # If we need subdivision and haven't exceeded max depth
            if needs_subdivision and current_depth < max_depth:
                subcells = self._subdivide_cell(current_lat, current_lng, current_radius)
                for sub_lat, sub_lng, sub_radius in subcells:
                    cells_to_process.append((sub_lat, sub_lng, sub_radius, current_depth + 1))
                
                logger.info(
                    "osm_cell_subdivided",
                    provider="osm",
                    original_cell=cell_id,
                    subcells_created=len(subcells),
                    depth=current_depth + 1,
                    max_depth=max_depth
                )
            elif needs_subdivision and current_depth >= max_depth:
                logger.warning(
                    "osm_cell_max_depth_reached",
                    provider="osm",
                    cell_id=cell_id,
                    depth=current_depth,
                    max_depth=max_depth
                )
        
        # Remove duplicates based on place ID
        seen_ids = set()
        unique_results = []
        for result in all_results:
            place_id = result.get("id")
            if place_id and place_id not in seen_ids:
                seen_ids.add(place_id)
                unique_results.append(result)
        
        logger.info(
            "osm_search_with_subdivision_complete",
            provider="osm",
            total_results=len(unique_results),
            original_cells=1,
            total_cells_processed=len(cells_to_process) + 1
        )
        
        return unique_results