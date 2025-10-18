# Backend/api/routers/google_dev.py
from __future__ import annotations

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from os import getenv

# Importeer de bestaande service (jouw pad)
try:
    from app.services.google_service import GooglePlacesService  # type: ignore
except Exception:
    from services.google_service import GooglePlacesService  # type: ignore

router = APIRouter(prefix="/dev/google", tags=["dev_google"])

def _svc() -> GooglePlacesService:
    api_key = getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY ontbreekt (exporteer in je shell).")
    return GooglePlacesService(api_key=api_key)

@router.get("/nearby")
async def nearby(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius: int = Query(1000, ge=1, le=50000, description="Radius in meters"),
    included_types: Optional[str] = Query(None, description="Comma-separated Google place types"),
    max_results: int = Query(20, ge=1, le=60, description="Cap across pagination"),
    language: Optional[str] = Query(None, description="e.g. 'nl'"),
):
    svc = _svc()
    types_list: Optional[List[str]] = None
    if included_types:
        types_list = [t.strip() for t in included_types.split(",") if t.strip()]

    try:
        data = await svc.search_nearby(
            lat=lat,
            lng=lng,
            radius=radius,
            included_types=types_list,   # None of list[str]
            max_results=max_results,
            language=language,
        )
        return {"ok": True, "count": len(data or []), "items": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Google Places error: {e}")

@router.get("/text")
async def text(
    q: str = Query(..., description="textQuery"),
    max_results: int = Query(20, ge=1, le=60, description="Cap across pagination"),
    language: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
):
    svc = _svc()
    try:
        data = await svc.search_text(
            text=q,                # ✅ juiste naam
            max_results=max_results,
            language=language,
            region=region,
        )
        return {"ok": True, "count": len(data or []), "items": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Google Places error: {e}")
    finally:
        await svc.aclose()
