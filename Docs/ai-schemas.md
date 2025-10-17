# AI Schemas – Unified Layer

**Doel:** Eén bron van waarheid voor alle AI-payloads (classify/enrich/verify). Dit verbetert consistentie, testbaarheid en onderhoud.

## Kernmodellen (Pydantic v2)
- `AIClassification` → { action, category, confidence_score, reason?, subcategory? }
- `AIEnrichment` → { name_normalized?, website, url_valid, rating, user_ratings_total, business_status?, opening_hours?, language_tags? }
- `AIVerificationResult` → { status, reasons?, evidence? }
- Hulp: `LocationRecord`, `GoldRecord`, `AuditEvent`, `GeoPoint`, `ContactInfo`, `OpeningHours`.

## Enums
- `Action` (KEEP/IGNORE), `Category`, `VerificationStatus` (CANDIDATE/VERIFIED/REJECTED), `BusinessStatus`.

## Normalizers
- URL normalisatie (scheme toevoegen, trailing slash strippen).
- Phone normalisatie (digits/+, minimale lengte).
- Language tags naar lower-case en deduplicatie.

## Backward-compat
- Aliassen: `confidence`/`score` → `confidence_score`; `websiteUri`/`url` → `website`.
- TODO-tags markeren voor deprecatie in volgende release.

## Validatie Helpers
Gebruik vanuit services/workers altijd de helpers:
```python
from app.services.ai_validation import (
  validate_classification_payload,
  validate_enrichment_payload,
  validate_verification_payload,
)
