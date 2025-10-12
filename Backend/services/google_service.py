# -*- coding: utf-8 -*-
"""
Google Places Service (async)
Compatibel met DiscoveryBot.

Vereist:
    - env variabele GOOGLE_API_KEY
    - pip install httpx

Gebruik:
    from app.services.google_service import GooglePlacesService
    svc = GooglePlacesService()
    results = await svc.search_nearby(51.9244, 4.4777, 1000, ["bakery"])
"""

from __future__ import annotations
import os
import asyncio
from typing import List, Dict, Any, Optional
import httpx
from dotenv import load_dotenv
load_dotenv()

# ---------------------------------------------------------------------------
# 1) Config
# ---------------------------------------------------------------------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"

# Field mask: enkel noodzakelijke velden (quota-efficiënt)
FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.location,"
    "places.types,places.rating,places.userRatingCount,places.businessStatus,"
    "places.websiteUri"
)

# ---------------------------------------------------------------------------
# 2) Service class
# ---------------------------------------------------------------------------
class GooglePlacesService:
    """Async wrapper om Google Places API v1 Nearby Search aan te roepen."""

    def __init__(self, api_key: Optional[str] = None, timeout_s: float = 15.0, max_retries: int = 5):
        # Gebruik env of expliciet meegegeven key
        self.api_key = api_key or GOOGLE_API_KEY
        if not self.api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY ontbreekt. Voeg deze toe aan .env of exporteer in je shell, "
                "bijv.: export GOOGLE_API_KEY='your_key_here'"
            )
        self.timeout_s = timeout_s
        self.max_retries = max_retries

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
        Voert een Nearby Search uit via de Places API v1.
        Retourneert een lijst met place-dicts.
        """
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        }
        body: Dict[str, Any] = {
            "includedTypes": included_types,
            "maxResultCount": max(1, min(int(max_results), 50)),
            "locationRestriction": {
                "circle": {"center": {"latitude": lat, "longitude": lng}, "radius": float(radius)}
            },
        }
        if language:
            body["languageCode"] = language

        backoff = 0.8
        last_err: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                    resp = await client.post(PLACES_NEARBY_URL, headers=headers, json=body)

                if resp.status_code == 200:
                    data = resp.json() or {}
                    return data.get("places") or []

                # Retrybare fouten
                if resp.status_code in (429, 500, 502, 503, 504):
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2.0, 8.0)
                    continue

                # Niet-retrybaar → raise direct
                raise RuntimeError(f"Google Places API error {resp.status_code}: {resp.text}")

            except Exception as e:
                last_err = e
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, 8.0)
                continue

        # alle pogingen mislukt
        if last_err:
            raise last_err
        return []
