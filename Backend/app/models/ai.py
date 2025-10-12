# app/models/ai.py
from __future__ import annotations

from typing import Optional, Literal
from pydantic import BaseModel, Field

class ClassificationResult(BaseModel):
    """
    Output-schema voor TDA-10/TDA-11.
    Dit schema wordt afgedwongen op het AI-antwoord.
    """
    action: Literal["keep", "ignore"] = Field(
        ..., description="Of de locatie relevant is voor de Turkse diaspora (keep) of niet (ignore)"
    )
    category: str = Field(
        ..., description="Primaire categorie (bv. 'bakery', 'restaurant', 'barber')"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Vertrouwensscore tussen 0.0 en 1.0"
    )
    reason: Optional[str] = Field(
        default=None, description="Korte motivatie (NL of TR)"
    )

class AIResponseEnvelope(BaseModel):
    """
    Optioneel envelopmodel voor debugging / logging pipelines.
    Niet verplicht voor de service, maar handig in tooling.
    """
    ok: bool
    model: str
    raw_text: str
    parsed: Optional[dict] = None
