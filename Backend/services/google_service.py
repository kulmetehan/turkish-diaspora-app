# Backend/services/google_service.py
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import httpx

PLACES_HOST = "https://places.googleapis.com/v1"

# Field mask ZONDER nextPageToken (vermijdt 400 in sommige regio's)
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

class GooglePlacesAPIError(RuntimeError):
    pass

class GooglePlacesService:
    def __init__(self, api_key: str, timeout_s: float = 15.0):
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def aclose(self):
        await self._client.aclose()

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Goog-Api-Key": self._api_key,
            # v1 vereist FIELD MASK als HEADER (niet als queryparam)
            "X-Goog-FieldMask": FIELD_MASK,
            "Content-Type": "application/json",
        }

    async def _post(self, path: str, json: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{PLACES_HOST}/{path}"
        backoff = 0.5
        last = None
        for _ in range(6):
            resp = await self._client.post(url, headers=self._headers(), json=json)
            if resp.status_code < 400:
                return resp.json()
            last = resp
            if resp.status_code in (429, 500, 502, 503, 504):
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 8.0)
                continue
            raise GooglePlacesAPIError(f"Google Places API error {resp.status_code}: {resp.text}")
        raise GooglePlacesAPIError(f"Google Places API retry exhausted: last={last.status_code if last else 'n/a'} {last.text if last else ''}")

    async def search_text(
        self,
        text: str,
        max_results: int = 20,
        language: Optional[str] = None,
        region: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "textQuery": text,
            "maxResultCount": min(20, max(1, int(max_results))),
        }
        if language:
            payload["languageCode"] = language
        if region:
            payload["regionCode"] = region

        items: List[Dict[str, Any]] = []
        next_page_token: Optional[str] = None
        while True:
            if next_page_token:
                payload["pageToken"] = next_page_token
            data = await self._post("places:searchText", payload)
            items.extend(data.get("places") or [])
            # NB: sommige regio's geven nextPageToken terug ook zonder mask
            next_page_token = data.get("nextPageToken")
            if not next_page_token or len(items) >= max_results:
                break
        return items[:max_results]

    async def search_nearby(
        self,
        lat: float,
        lng: float,
        radius: int,
        included_types: Optional[List[str]] = None,
        max_results: int = 20,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "maxResultCount": min(20, max(1, int(max_results))),
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius),
                }
            },
        }
        if included_types:
            payload["includedTypes"] = included_types
        if language:
            payload["languageCode"] = language

        items: List[Dict[str, Any]] = []
        next_page_token: Optional[str] = None
        while True:
            if next_page_token:
                payload["pageToken"] = next_page_token
            data = await self._post("places:searchNearby", payload)
            places = data.get("places") or []
            items.extend(places)
            # NB: sommige regio's geven nextPageToken terug ook zonder mask
            next_page_token = data.get("nextPageToken")
            if not next_page_token or len(items) >= max_results:
                break
        return items[:max_results]
