# -*- coding: utf-8 -*-
"""
Google Places Service (async) – v1 Nearby Search
- Clampt per-call resultaten op 20 (API limiet).
- Ondersteunt paginatie via nextPageToken om tot 'requested_total' per cel te halen.

Vereist:
  - env GOOGLE_API_KEY
  - pip install httpx python-dotenv
"""

from __future__ import annotations
import os
import asyncio
from typing import List, Dict, Any, Optional
import httpx

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"

# Hou het field mask klein (quota/latency)
FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.location,"
    "places.types,places.rating,places.userRatingCount,places.businessStatus,"
    "places.websiteUri,nextPageToken"
)

class GooglePlacesService:
    """Async wrapper voor Google Places v1 Nearby Search."""

    def __init__(self, api_key: Optional[str] = None, timeout_s: float = 15.0, max_retries: int = 5):
        self.api_key = api_key or GOOGLE_API_KEY
        if not self.api_key:
            raise RuntimeError("GOOGLE_API_KEY ontbreekt (env).")
        self.timeout_s = timeout_s
        self.max_retries = max_retries

    async def _single_call(
        self,
        *,
        lat: float,
        lng: float,
        radius_m: int,
        included_types: List[str],
        page_size: int,
        page_token: Optional[str],
        language: Optional[str],
    ) -> Dict[str, Any]:
        """Doet één POST naar places:searchNearby."""
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        }
        body: Dict[str, Any] = {
            "includedTypes": included_types,
            # API max 20 per call
            "maxResultCount": max(1, min(int(page_size), 20)),
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius_m),
                }
            },
        }
        if language:
            body["languageCode"] = language
        if page_token:
            body["pageToken"] = page_token

        backoff = 0.8
        last_err: Optional[Exception] = None

        for _ in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                    resp = await client.post(PLACES_NEARBY_URL, headers=headers, json=body)

                if resp.status_code == 200:
                    return resp.json() or {}

                if resp.status_code in (429, 500, 502, 503, 504):
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2.0, 8.0)
                    continue

                # Niet-retrybaar
                raise RuntimeError(f"Google Places API error {resp.status_code}: {resp.text}")

            except Exception as e:
                last_err = e
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, 8.0)

        if last_err:
            raise last_err
        return {}

    async def search_nearby(
        self,
        lat: float,
        lng: float,
        radius: int,
        included_types: List[str],
        max_results: int = 20,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Haalt tot 'max_results' items binnen door pagina's (20 per call) op te vragen.
        """
        requested_total = max(1, int(max_results))
        results: List[Dict[str, Any]] = []
        next_token: Optional[str] = None

        while len(results) < requested_total:
            page_size = min(20, requested_total - len(results))
            data = await self._single_call(
                lat=lat,
                lng=lng,
                radius_m=radius,
                included_types=included_types,
                page_size=page_size,
                page_token=next_token,
                language=language,
            )

            places = data.get("places") or []
            results.extend(places)

            next_token = data.get("nextPageToken")
            if not next_token:
                break

            # v1 is meestal direct pageable, maar wees lief voor quota
            await asyncio.sleep(1.2)

        # truncate als er onverhoopt meer kwam
        return results[:requested_total]
