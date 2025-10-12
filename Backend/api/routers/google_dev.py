from fastapi import APIRouter, Query, HTTPException
import httpx
from services.google_service import GooglePlacesService
from app.config import settings

router = APIRouter(prefix="/dev/google", tags=["dev-google"])

def _svc() -> GooglePlacesService:
    return GooglePlacesService(
        api_key=settings.GOOGLE_API_KEY,
        language_code=getattr(settings, "GOOGLE_PLACES_LANGUAGE", "nl"),
        region_code=getattr(settings, "GOOGLE_PLACES_REGION", "NL"),
    )

@router.get("/text")
async def text_search(q: str = Query(..., min_length=2), max_results: int = 20):
    svc = _svc()
    try:
        items = await svc.search_text(q, max_results=max_results)
        return {"count": len(items), "items": items}
    except httpx.HTTPStatusError as exc:
        # Google API returned an error status
        raise HTTPException(
            status_code=502,
            detail=f"Google Places returned {exc.response.status_code}"
        )
    except httpx.RequestError as exc:
        # Network error
        raise HTTPException(
            status_code=502,
            detail=f"Network error to Google: {str(exc)}"
        )
    finally:
        await svc.aclose()

@router.get("/nearby")
async def nearby(lat: float, lng: float, radius: int = 1500, max_results: int = 20):
    svc = _svc()
    try:
        items = await svc.search_nearby(lat, lng, radius, max_results=max_results)
        return {"count": len(items), "items": items}
    except httpx.HTTPStatusError as exc:
        # Google API returned an error status
        raise HTTPException(
            status_code=502,
            detail=f"Google Places returned {exc.response.status_code}"
        )
    except httpx.RequestError as exc:
        # Network error
        raise HTTPException(
            status_code=502,
            detail=f"Network error to Google: {str(exc)}"
        )
    finally:
        await svc.aclose()