# api/routers/dev_ai.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from services.openai_service import OpenAIService
from app.models.ai import ClassificationResult

router = APIRouter(prefix="/dev/ai", tags=["dev-ai"])

@router.get("/ping")
def ping():
    return {"ok": True, "service": "dev_ai"}

@router.post("/classify-demo")
def classify_demo(
    name: str = Query(..., description="Naam van de kandidaat-zaak"),
    address: str = Query(..., description="Adres"),
    typ: str = Query(..., description="Ruwe type/bron (bv. 'bakery', 'restaurant')"),
):
    """
    Demo endpoint voor TDA-10:
    - Dwingt JSON via OpenAIService + Pydantic schema (ClassificationResult)
    - Logt input/output/usage in ai_logs (als db_service.ai_log aanwezig is)
    """
    system = (
        "Je bent een classifier voor Turkse diaspora-locaties in Nederland. "
        "Beantwoord uitsluitend in het Nederlands of Turks."
    )
    user = (
        f"Geef classificatie voor:\n"
        f"- Naam: {name}\n"
        f"- Adres: {address}\n"
        f"- Ruw type: {typ}\n\n"
        f"Regels: retourneer ALLEEN geldige JSON volgens het schema."
    )

    svc = OpenAIService()
    try:
        parsed, meta = svc.generate_json(
            system_prompt=system,
            user_prompt=user,
            response_model=ClassificationResult,
            action_type="classify_demo",
        )
        return {"ok": True, "parsed": parsed.model_dump(), "meta": meta}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
