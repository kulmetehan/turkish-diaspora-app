---
title: AI Schemas — Unified Layer
status: active
last_updated: 2025-11-04
scope: backend
owners: [tda-core]
---

# AI Schemas — Unified Layer

Defines the Pydantic models and helpers that unify AI inputs/outputs across classification, enrichment, and verification flows.

## Location of truth

- `Backend/app/models/ai.py` — canonical enums, models, validators, and `TypeAdapter`s.
- `Backend/services/ai_validation.py` — helper functions (`validate_classification_payload`, etc.) wrapping the adapters and raising `AIValidationError` on failure.

## Enums

| Enum | Values | Usage |
| --- | --- | --- |
| `Action` | `keep`, `ignore` | Classification decision driving state transitions. |
| `Category` | `bakery`, `restaurant`, `supermarket`, `barbershop`, `mosque`, `travel_agency`, `other` | Canonical categories; keep in sync with frontend icons and discovery config. |
| `VerificationStatus` | `CANDIDATE`, `VERIFIED`, `REJECTED` | Used by verification payloads and location records. |
| `BusinessStatus` | `OPERATIONAL`, `TEMPORARILY_CLOSED`, `PERMANENTLY_CLOSED`, `UNKNOWN` | Captures enrichment data about business state. |

## Core models

### `AIClassification`

```json
{
  "action": "keep",
  "category": "bakery",
  "confidence_score": 0.92,
  "reason": "Baklava specialty"
}
```

- Accepts legacy keys (`confidence`, `score`).
- Confidence automatically clipped to `[0,1]`.

### `AIEnrichment`

```json
{
  "name_normalized": "Saray Baklava",
  "website": "https://saraybaklava.nl",
  "rating": 4.5,
  "user_ratings_total": 120,
  "business_status": "OPERATIONAL",
  "language_tags": ["tr", "nl"]
}
```

- URLs normalized (scheme added, trailing slash removed). Invalid URLs raise `url_invalid`.
- Phone numbers normalized to digits/+ only with minimum length check.
- `language_tags` deduplicated and lowercased.

### `AIVerificationResult`

```json
{
  "status": "VERIFIED",
  "reasons": ["OpenAI classification keep"],
  "evidence": [
    { "source": "verify_locations", "url": "https://...", "notes": "Google listing" }
  ]
}
```

- Evidence URLs normalized just like enrichment URLs.

### `LocationRecord`

Unified DTO for AI ↔ backend interactions. Includes geo point, contact info, categories, and optional enrichment fields.

### Supporting models

- `OpeningHours`, `Evidence`, `GeoPoint`, `ContactInfo`, `GoldRecord`, `AuditEvent`.

## Validation helpers

```python
from services.ai_validation import (
    validate_classification_payload,
    validate_enrichment_payload,
    validate_verification_payload,
)

classification = validate_classification_payload(raw_dict)
```

- Return strongly typed models; raise `AIValidationError` with original payload on failure.
- Used by workers (`classify_bot`, `verify_locations`) and API endpoints.

## Backward compatibility

- Legacy aliases: `confidence`, `score` → `confidence_score`; `websiteUri` / `url` → `website`.
- `ClassificationResult = AIClassification` exported for older modules.

## Maintenance tips

- Update this document whenever enums or fields change.
- Add new few-shot examples in [`Backend/services/prompts/classify_fewshot_nltr.md`](../Backend/services/prompts/classify_fewshot_nltr.md).
- Regenerate OpenAPI docs after schema changes to ensure clients stay in sync.
