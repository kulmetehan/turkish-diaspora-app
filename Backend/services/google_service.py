# app/services/google_service.py
from __future__ import annotations

import asyncio
import math
import random
from typing import Any, Dict, List, Optional, Tuple

import httpx
import structlog

from app.core.config import settings

log = structlog.get_logger(__name__)

# Google Places API v1 endpoints (legal, no scraping)
PLACES_BASE = "https://places.googleapis.com/v1"
ENDPOINT_TEXT_SEARCH = f"{PLACES_BASE}/places:searchText"
ENDPOINT_NEARBY_SEARCH = f"{PLACES_BASE}/places:searchNearby"

# Minimal, quota-efficient field mask (ask only what we need)
# See Master Plan: data minimization & cost control.
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.types",
    "places.rating",
    "places.userRatingCount",
    "places.businessStatus",
    "places.websiteUri",
])

DEFAULT_TIMEOUT = httpx.Timeout(10.0, read=20.0)
MAX_PAGE_RESULTS = 20  # per Google spec
DEFAULT_MAX_RESULTS = 60  # paginate up to 3 pages by default

class GooglePlacesService:
    def __init__(
        self,
        api_key: str,
        language_code: str = "nl",
        region_code: str = "NL",
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.api_key = api_key
        self.language_code = language_code
        self.region_code = region_code
        self._client = client

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": FIELD_MASK,  # field mask for quota efficiency
            "Content-Type": "application/json",
        }

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        return self._client

    async def _post_with_retries(
        self,
        url: str,
        json_payload: Dict[str, Any],
        max_retries: int = 5,
        base_delay: float = 0.5,
        max_delay: float = 8.0,
    ) -> httpx.Response:
        """
        Exponential backoff with jitter.
        Retries on 429 / 5xx / network errors. Respects Retry-After when present.
        """
        attempt = 0
        while True:
            client = await self._ensure_client()
            try:
                resp = await client.post(url, headers=self._headers(), json=json_payload)
                # Log every call for auditing/cost tracking
                log.info(
                    "google_api_call",
                    endpoint=url,
                    status_code=resp.status_code,
                    payload_summary=_summarize_payload(json_payload),
                    request_id=_extract_req_id(resp),
                )

                if resp.status_code == 200:
                    return resp

                # Respect rate limiting
                if resp.status_code in (429, 503):
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after:
                        delay = float(retry_after)
                    else:
                        delay = min(max_delay, base_delay * (2 ** attempt)) * (1 + random.random() * 0.25)
                    attempt += 1
                    if attempt > max_retries:
                        _log_error(resp, "max_retries_exceeded")
                        resp.raise_for_status()
                    log.warning("google_api_backoff", status_code=resp.status_code, delay=delay, attempt=attempt)
                    await asyncio.sleep(delay)
                    continue

                # 4xx other than 429 are considered terminal (bad request, auth, etc.)
                if 400 <= resp.status_code < 500:
                    _log_error(resp, "client_error")
                    resp.raise_for_status()

                # 5xx without explicit 503 => retry
                if 500 <= resp.status_code < 600:
                    attempt += 1
                    if attempt > max_retries:
                        _log_error(resp, "server_error_max_retries")
                        resp.raise_for_status()
                    delay = min(max_delay, base_delay * (2 ** attempt)) * (1 + random.random() * 0.25)
                    log.warning("google_api_backoff", status_code=resp.status_code, delay=delay, attempt=attempt)
                    await asyncio.sleep(delay)
                    continue

                return resp  # fallback

            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.NetworkError) as exc:
                attempt += 1
                if attempt > max_retries:
                    log.error("google_api_network_error", error=str(exc), attempt=attempt)
                    raise
                delay = min(max_delay, base_delay * (2 ** attempt)) * (1 + random.random() * 0.25)
                log.warning("google_api_network_backoff", delay=delay, attempt=attempt, error=str(exc))
                await asyncio.sleep(delay)

    async def search_text(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        language_code: Optional[str] = None,
        region_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Text Search: e.g., 'Turkse bakkerij Rotterdam'
        Returns a normalized list of places.
        """
        results: List[Dict[str, Any]] = []
        page_token: Optional[str] = None
        language = language_code or self.language_code
        region = region_code or self.region_code

        while len(results) < max_results:
            body: Dict[str, Any] = {
                "textQuery": query,
                "languageCode": language,
                "maxResultCount": min(MAX_PAGE_RESULTS, max_results - len(results)),
            }
            # region bias if provided
            if region:
                body["regionCode"] = region

            if page_token:
                body["pageToken"] = page_token

            resp = await self._post_with_retries(ENDPOINT_TEXT_SEARCH, body)
            data = resp.json()
            places = data.get("places", [])
            results.extend([_normalize_place(p) for p in places if p])

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return results

    async def search_nearby(
        self,
        lat: float,
        lng: float,
        radius_meters: int,
        included_types: Optional[List[str]] = None,
        max_results: int = DEFAULT_MAX_RESULTS,
        language_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Nearby Search within a circle (lat/lng + radius).
        """
        results: List[Dict[str, Any]] = []
        page_token: Optional[str] = None
        language = language_code or self.language_code

        while len(results) < max_results:
            body: Dict[str, Any] = {
                "languageCode": language,
                "maxResultCount": min(MAX_PAGE_RESULTS, max_results - len(results)),
                "locationRestriction": {
                    "circle": {
                        "center": {"latitude": lat, "longitude": lng},
                        "radius": radius_meters,
                    }
                },
                # Popularity sorting reduces random churn; you can switch to DISTANCE if needed
                "rankPreference": "POPULARITY",
            }
            if included_types:
                body["includedTypes"] = included_types
            if page_token:
                body["pageToken"] = page_token

            resp = await self._post_with_retries(ENDPOINT_NEARBY_SEARCH, body)
            data = resp.json()
            places = data.get("places", [])
            results.extend([_normalize_place(p) for p in places if p])

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return results

    async def aclose(self) -> None:
        if self._client:
            await self._client.aclose()

def _normalize_place(p: Dict[str, Any]) -> Dict[str, Any]:
    """Return only the fields we actually need (data minimization)."""
    # v1 uses displayName -> {'text': 'Name'}
    name = (p.get("displayName") or {}).get("text")
    loc = p.get("location") or {}
    return {
        "id": p.get("id"),
        "name": name,
        "formatted_address": p.get("formattedAddress"),
        "lat": loc.get("latitude"),
        "lng": loc.get("longitude"),
        "types": p.get("types"),
        "rating": p.get("rating"),
        "user_ratings_total": p.get("userRatingCount"),
        "business_status": p.get("businessStatus"),
        "website": p.get("websiteUri"),
    }

def _extract_req_id(resp: httpx.Response) -> Optional[str]:
    # Google often sends request-id headers; capture if present for cross-system tracing
    return resp.headers.get("x-request-id") or resp.headers.get("x-guploader-uploadid")

def _summarize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Keep logs PII-free & minimal; summarize
    out = {}
    for k in ("textQuery", "languageCode", "regionCode", "rankPreference", "maxResultCount", "pageToken"):
        if k in payload:
            out[k] = payload[k]
    if "locationRestriction" in payload:
        circ = payload["locationRestriction"].get("circle", {})
        out["locationRestriction"] = {
            "lat": (circ.get("center") or {}).get("latitude"),
            "lng": (circ.get("center") or {}).get("longitude"),
            "radius": circ.get("radius"),
        }
    if "includedTypes" in payload:
        out["includedTypes"] = payload["includedTypes"]
    return out


def _log_error(resp: httpx.Response, tag: str) -> None:
    """Log Google API errors with structured context."""
    try:
        data = resp.json()
        err = (data or {}).get("error", {})
        message = err.get("message")
        status = err.get("status")
        details = err.get("details")
    except Exception:
        data = None
        message = None
        status = None
        details = None

    log.error(
        "google_api_error",
        tag=tag,
        status_code=resp.status_code,
        error_message=message,
        error_status=status,
        details=details,
        snippet=resp.text[:500] if not data else None,
    )