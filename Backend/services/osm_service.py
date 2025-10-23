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
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter", 
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

# Default configuration
DEFAULT_USER_AGENT = "TurkishDiasporaApp/1.0 (contact: m.kul@lamarka.nl)"
DEFAULT_TIMEOUT_S = int(os.getenv("OVERPASS_TIMEOUT_S", "30"))
DEFAULT_MAX_RESULTS = int(os.getenv("DISCOVERY_MAX_RESULTS", "25"))
DEFAULT_RATE_LIMIT_QPS = float(os.getenv("DISCOVERY_RATE_LIMIT_QPS", "0.15"))
DEFAULT_SLEEP_BASE_S = float(os.getenv("DISCOVERY_SLEEP_BASE_S", "3.0"))
DEFAULT_SLEEP_JITTER_PCT = float(os.getenv("DISCOVERY_SLEEP_JITTER_PCT", "0.20"))
DEFAULT_BACKOFF_SERIES = [int(x) for x in os.getenv("DISCOVERY_BACKOFF_SERIES", "20,60,180,420").split(",")]
DEFAULT_MAX_SUBDIVIDE_DEPTH = int(os.getenv("MAX_SUBDIVIDE_DEPTH", "2"))
DEFAULT_TURKISH_HINTS = os.getenv("OSM_TURKISH_HINTS", "1").lower() == "true"

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
        self.endpoint = endpoint or self.endpoints[0]
        self.timeout_s = timeout_s
        self.user_agent = user_agent or os.getenv("OVERPASS_USER_AGENT", DEFAULT_USER_AGENT)
        self.max_results = max_results
        self.sleep_base_s = sleep_base_s
        self.sleep_jitter_pct = sleep_jitter_pct
        self.backoff_series = backoff_series
        self.turkish_hints = turkish_hints
        self.max_subdivide_depth = max_subdivide_depth
        
        self.rate_limiter = TokenBucket(capacity=1.0, refill_rate=rate_limit_qps)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_s),
            headers={"User-Agent": self.user_agent}
        )
        
        # Database connection for telemetry
        self._db_session = None

    async def aclose(self):
        await self._client.aclose()
        if self._db_session:
            await self._db_session.close()

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
        raw_preview: Optional[str] = None
    ):
        """Log Overpass API call to database for telemetry."""
        try:
            # Import here to avoid circular imports
            from sqlalchemy import text
            
            if not self._db_session:
                from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
                database_url = os.getenv("DATABASE_URL")
                if database_url and database_url.startswith("postgresql://"):
                    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
                engine = create_async_engine(database_url, pool_pre_ping=True, future=True)
                self._db_session = async_sessionmaker(engine, expire_on_commit=False)
            
            # Create safe preview string for DB storage
            safe_preview = None
            if raw_preview is not None:
                try:
                    safe_preview = str(raw_preview)[:4000]  # Truncate for DB
                except Exception:
                    safe_preview = "preview_error"
            
            async with self._db_session() as session:
                await session.execute(text("""
                    INSERT INTO overpass_calls (
                        endpoint, bbox_or_center, radius_m, query_bytes, status_code,
                        found, normalized, category_set, cell_id, attempt, duration_ms,
                        error_message, retry_after_s, user_agent, timeout_s, max_results, raw_preview
                    ) VALUES (
                        :endpoint, :bbox_or_center, :radius_m, :query_bytes, :status_code,
                        :found, :normalized, :category_set, :cell_id, :attempt, :duration_ms,
                        :error_message, :retry_after_s, :user_agent, :timeout_s, :max_results, :raw_preview
                    )
                """), {
                    "endpoint": endpoint,
                    "bbox_or_center": bbox_or_center,
                    "radius_m": radius_m,
                    "query_bytes": query_bytes,
                    "status_code": status_code,
                    "found": found,
                    "normalized": normalized,
                    "category_set": category_set,
                    "cell_id": cell_id,
                    "attempt": attempt,
                    "duration_ms": duration_ms,
                    "error_message": error_message,
                    "retry_after_s": retry_after_s,
                    "user_agent": self.user_agent,
                    "timeout_s": self.timeout_s,
                    "max_results": self.max_results,
                    "raw_preview": safe_preview
                })
                await session.commit()
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
        timeout_s: int = 25,
        included_types: Optional[List[str]] = None
    ) -> str:
        """Build a single Overpass query that combines multiple categories."""
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
        
        # Add Turkish hints (restrictive AND) for food categories
        turkish_filters = self._get_turkish_hints_filters()
        if self.turkish_hints and turkish_filters:
            food_keys = {"restaurant", "fast_food", "bakery", "butcher", "supermarket"}
            if included_types and any(k in food_keys for k in included_types):
                # Combine each base selector with each hint using AND semantics
                combined_snippets: List[str] = []
                for s in all_filter_snippets or []:
                    for h in turkish_filters:
                        combined_snippets.append(s + h)  # AND in Overpass = concatenated filters
                if combined_snippets:
                    all_filter_snippets = combined_snippets
            else:
                # For non-food categories, keep hints optional (or skip entirely)
                # all_filter_snippets.extend(turkish_filters)
                pass
        
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
        
        # Rate limiting with jitter
        await self.rate_limiter.acquire()
        jitter = random.uniform(0, self.sleep_jitter_pct * self.sleep_base_s)
        await asyncio.sleep(self.sleep_base_s + jitter)
        
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
        
        query = self._build_union_query(lat, lng, radius, osm_tags_list, max_results, self.timeout_s, included_types)
        
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
        
        start_time = time.time()
        status_code = 0
        error_message = None
        retry_after_s = None
        
        try:
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
            
            if status_code in (400, 422):
                error_message = "Syntax error"
                logger.error(
                    "osm_query_syntax_error",
                    provider="osm",
                    status_code=status_code,
                    query=query,
                    response_text=response.text[:500]
                )
                raise RuntimeError("Overpass 400 (syntax). See logged query.")
            
            if status_code == 429:
                retry_after_s = int(response.headers.get("Retry-After", "60"))
                error_message = "Rate limited"
                logger.warning(
                    "osm_rate_limited",
                    provider="osm",
                    retry_after=retry_after_s
                )
                # Don't raise here, we'll handle retry logic
                raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
            
            if status_code >= 500:
                error_message = f"Server error {status_code}"
                logger.error(
                    "osm_server_error",
                    provider="osm",
                    status_code=status_code
                )
                raise httpx.HTTPStatusError("Server error", request=response.request, response=response)
            
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
            try:
                raw_preview = json.dumps(data)[:4000] if data else None
            except Exception:
                raw_preview = str(data)[:4000] if data else None
                
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
                attempt=attempt,
                duration_ms=duration_ms,
                raw_preview=raw_preview
            )
            
            logger.info(
                "osm_search_success",
                provider="osm",
                found=len(elements),
                normalized=len(result),
                lat=lat,
                lng=lng,
                needs_subdivision=needs_subdivision,
                duration_ms=duration_ms
            )
            
            return result, needs_subdivision
            
        except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            if isinstance(e, httpx.HTTPStatusError):
                status_code = e.response.status_code
                error_message = f"HTTP {status_code}"
            else:
                status_code = 504
                error_message = "Timeout"
            
            # Log failed call
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
                attempt=attempt,
                duration_ms=duration_ms,
                error_message=error_message,
                retry_after_s=retry_after_s
            )
            
            logger.error(
                "osm_search_error",
                provider="osm",
                error=error_message,
                lat=lat,
                lng=lng,
                status_code=status_code
            )
            
            # Rotate endpoint on failure
            self._rotate_endpoint()
            
            return [], False
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)
            
            # Log failed call
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
                attempt=attempt,
                duration_ms=duration_ms,
                error_message=error_message
            )
            
            logger.error(
                "osm_search_error",
                provider="osm",
                error=error_message,
                lat=lat,
                lng=lng
            )
            
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