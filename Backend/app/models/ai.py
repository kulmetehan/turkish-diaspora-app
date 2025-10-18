# Backend/app/models/ai.py
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
import re
from urllib.parse import urlparse

from pydantic import BaseModel, Field, AliasChoices, ValidationError, field_validator, TypeAdapter, model_validator
from pydantic_core import PydanticCustomError


# =========================
# Enums
# =========================

class Action(str, Enum):
    KEEP = "keep"
    IGNORE = "ignore"


class Category(str, Enum):
    bakery = "bakery"
    restaurant = "restaurant"
    supermarket = "supermarket"
    barbershop = "barbershop"
    mosque = "mosque"
    travel_agency = "travel_agency"
    other = "other"


class VerificationStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class BusinessStatus(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    TEMPORARILY_CLOSED = "TEMPORARILY_CLOSED"
    PERMANENTLY_CLOSED = "PERMANENTLY_CLOSED"
    UNKNOWN = "UNKNOWN"


# =========================
# Normalizers
# =========================

def _normalize_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = value.strip()
    # scheme toevoegen indien ontbreekt
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", v):
        v = "https://" + v
    try:
        parsed = urlparse(v)
        if not parsed.netloc:
            raise ValueError("URL missing host")
        normalized = (parsed.scheme + "://" + parsed.netloc + (parsed.path or "")).rstrip("/")
        return normalized
    except Exception:
        raise PydanticCustomError("url_invalid", "Invalid website URL")


def _normalize_phone(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = re.sub(r"[^\d+]", "", value)
    if len(re.sub(r"[^\d]", "", digits)) < 7:
        raise PydanticCustomError("phone_invalid", "Invalid phone number")
    return digits


def _clip01(x: Optional[float]) -> Optional[float]:
    if x is None:
        return None
    return max(0.0, min(1.0, x))


# =========================
# Kern-entiteiten
# =========================

class AIClassification(BaseModel):
    """
    Unified classification-output (TDA-10/TDA-11).
    Backward-compat:
      - validation_alias: confidence|score -> confidence_score
    """
    action: Action = Field(..., description="keep/ignore decision")
    category: Category = Field(default=Category.other)
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="0..1",
        validation_alias=AliasChoices("confidence_score", "confidence", "score"),
    )
    reason: Optional[str] = None
    subcategory: Optional[str] = None

    @field_validator("confidence_score", mode="before")
    @classmethod
    def _coerce_and_clip_conf(cls, v: Any) -> float:
        try:
            f = float(v)
        except Exception:
            raise PydanticCustomError("confidence_invalid", "confidence_score must be float in [0,1]")
        # CLIP vóór constraints zodat 1.2 niet faalt maar 1.0 wordt
        return _clip01(f) or 0.0


class OpeningHours(BaseModel):
    weekday_text: Optional[List[str]] = None  # e.g., ["Mon: 09:00–18:00", ...]
    is_open_now: Optional[bool] = None


class AIEnrichment(BaseModel):
    """
    Enrichment/normalization uit Google/AI.
    Backward-compat:
      - websiteUri|url -> website
    """
    name_normalized: Optional[str] = None
    website: Optional[str] = Field(default=None, validation_alias=AliasChoices("website", "websiteUri", "url"))
    url_valid: Optional[bool] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    user_ratings_total: Optional[int] = Field(default=None, ge=0)
    business_status: Optional[BusinessStatus] = None
    opening_hours: Optional[OpeningHours] = None
    language_tags: Optional[List[str]] = None  # ["tr","nl","en"]

    @field_validator("website", mode="after")
    @classmethod
    def _normalize_site(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return _normalize_url(v)

    @field_validator("url_valid", mode="after")
    @classmethod
    def _derive_url_valid(cls, v: Optional[bool], info):
        # Na normalisatie: als expliciet gezet → respecteren, anders afleiden
        if v is not None:
            return bool(v)
        website = info.data.get("website")
        return bool(website)

    @field_validator("language_tags")
    @classmethod
    def _clean_langs(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if not v:
            return v
        out: List[str] = []
        seen: Set[str] = set()
        for t in v:
            if not t:
                continue
            tag = t.strip().lower()
            if tag and tag not in seen:
                seen.add(tag)
                out.append(tag)
        return out

    @model_validator(mode="after")
    def _ensure_url_valid(self):
        # Als url_valid niet expliciet gezet is, dan afleiden uit website (na normalisatie)
        if self.url_valid is None:
            self.url_valid = bool(self.website)
        return self


class Evidence(BaseModel):
    source: Optional[str] = None  # e.g., "google_places", "admin"
    url: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("url")
    @classmethod
    def _norm_evidence_url(cls, v):
        return _normalize_url(v) if v else None


class AIVerificationResult(BaseModel):
    status: VerificationStatus
    reasons: Optional[List[str]] = None
    evidence: Optional[List[Evidence]] = None


class GeoPoint(BaseModel):
    lat: float
    lng: float


class ContactInfo(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def _norm_phone(cls, v):
        return _normalize_phone(v)

    @field_validator("website")
    @classmethod
    def _norm_site(cls, v):
        return _normalize_url(v)


class LocationRecord(BaseModel):
    """
    Minimale DTO van de locatie voor AI-/API-uitwisseling.
    """
    id: Optional[int] = None
    source: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    geo: Optional[GeoPoint] = None
    contact: Optional[ContactInfo] = None
    categories: Optional[List[Category]] = None

    ai_fields: Optional[AIEnrichment] = None
    confidence_score: Optional[float] = Field(default=None, ge=0, le=1)
    state: Optional[VerificationStatus] = None

    @field_validator("categories")
    @classmethod
    def _dedup_cats(cls, v):
        if not v:
            return v
        seen: Set[Category] = set()
        out: List[Category] = []
        for c in v:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out


class GoldRecord(BaseModel):
    is_gold_standard: bool = True
    provenance: Optional[str] = None  # bv. "admin_ui"
    admin_user_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AuditEvent(BaseModel):
    actor: str  # "system" | "admin:{id}" | "bot:verification"
    action: str  # "create" | "update" | "verify" | ...
    target_id: Optional[int] = None
    diff: Optional[Dict[str, Any]] = None
    ts: datetime = Field(default_factory=datetime.utcnow)


# =========================
# TypeAdapters & errors
# =========================

TA_CLASSIFICATION = TypeAdapter(AIClassification)
TA_ENRICHMENT = TypeAdapter(AIEnrichment)
TA_VERIFICATION = TypeAdapter(AIVerificationResult)


class AIValidationError(ValueError):
    def __init__(self, msg: str, payload: Any | None = None):
        super().__init__(msg)
        self.payload = payload


def validate_classification(data: Dict[str, Any]) -> AIClassification:
    try:
        return TA_CLASSIFICATION.validate_python(data, by_name=True)
    except ValidationError as e:
        raise AIValidationError(f"classification invalid: {e}", payload=data)


def validate_enrichment(data: Dict[str, Any]) -> AIEnrichment:
    try:
        return TA_ENRICHMENT.validate_python(data, by_name=True)
    except ValidationError as e:
        raise AIValidationError(f"enrichment invalid: {e}", payload=data)


def validate_verification(data: Dict[str, Any]) -> AIVerificationResult:
    try:
        return TA_VERIFICATION.validate_python(data, by_name=True)
    except ValidationError as e:
        raise AIValidationError(f"verification invalid: {e}", payload=data)


# =========================
# Backward-compatible aliases
# =========================
# Houd dev_ai.py en oudere endpoints werkend:
ClassificationResult = AIClassification
